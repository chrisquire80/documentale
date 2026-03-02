from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, update as sa_update
import google.generativeai as genai
from uuid import UUID

from ..db import get_db
from ..models.user import User
from ..models.document import Document, DocumentContent, DocumentMetadata
from ..models.folder import Folder
from ..api.auth import get_current_user
from ..schemas.ai_schemas import (
    ChatQueryRequest, ChatResponse, ChatSource, ExtractEntitiesResponse,
)
from ..services.embeddings import generate_query_embedding
from ..core.config import settings

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini integration is disabled or not configured.")

    # 1. Genera l'embedding della domanda utente
    try:
        query_embedding = await generate_query_embedding(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore generazione embedding: {str(e)}")

    if not query_embedding:
        raise HTTPException(status_code=500, detail="Impossibile generare l'embedding per la query.")

    # 2. Cerca nel database con pgvector
    # Usiamo lo spazio vettoriale cosine distance (<=>)
    stmt = """
        SELECT c.id, c.document_id, c.fulltext_content, d.title, d.is_restricted,
               (c.embedding <=> :query_embedding::vector) as distance
        FROM doc_content c
        JOIN documents d ON c.document_id = d.id
        WHERE d.is_deleted = false 
          AND c.embedding IS NOT NULL
          AND (d.owner_id = :user_id OR d.is_restricted = false)
    """
    
    params = {
        "query_embedding": str(query_embedding),
        "user_id": str(current_user.id)
    }

    # Se document_id è specificato, confina la ricerca
    if request.document_id:
        stmt += " AND d.id = :doc_id"
        params["doc_id"] = str(request.document_id)

    # Ordina per similarità e limita
    stmt += " ORDER BY distance ASC LIMIT 5"

    try:
        results = await db.execute(text(stmt), params)
        rows = results.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore query database vettoriale: {str(e)}")

    # 3. Prepara il contesto
    if not rows:
        return ChatResponse(
            answer="Non ho trovato documenti pertinenti nel tuo archivio per rispondere a questa domanda.",
            sources=[]
        )

    context_text = ""
    sources = []
    
    for row in rows:
        # row: id, document_id, fulltext_content, title, is_restricted, distance
        doc_id = str(row[1])
        fulltext = row[2] or ""
        title = row[3]
        
        # Prendi un estratto (primi 500 caratteri)
        snippet = fulltext[:500] + "..." if len(fulltext) > 500 else fulltext
        
        context_text += f"\n--- Documento: {title} (ID: {doc_id}) ---\n{snippet}\n"
        
        sources.append(ChatSource(
            document_id=doc_id,
            title=title,
            snippet=snippet[:150] + "..." # Snippet più corto per la risposta JSON
        ))

    # 4. prompt Gemini con Retrieval-Augmented Generation
    prompt = f"""
Sei un assistente aziendale intelligente e professionale. Rispondi alla domanda dell'utente basandoti ESCLUSIVAMENTE sul seguente contesto estratto dai documenti aziendali.

CONTESTO:
{context_text}

DOMANDA UTENTE: {request.query}

ISTRUZIONI:
- Rispondi in italiano in modo chiaro, conciso e diretto.
- Se la risposta non è presente nel contesto, dichiara apertamente che non hai informazioni sufficienti nei documenti forniti, e NON inventare nulla.
- Cita sempre le fonti (es. "In base al documento X...").
"""

    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Usiamo flash o pro, optiamo per flash per velocità
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    
    try:
        # Facciamo generare la risposta a Gemini (è sincrono quindi usiamo asyncio.to_thread se servisse, ma per ora lo chiamiamo in linea considerando le policy di app IO)
        import asyncio
        response = await asyncio.to_thread(model.generate_content, prompt)
        answer = response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore chiamata Gemini: {str(e)}")

    return ChatResponse(
        answer=answer,
        sources=sources
    )


# ── LangExtract: on-demand structured entity extraction ──────────────────────

@router.post("/extract/{doc_id}", response_model=ExtractEntitiesResponse)
async def extract_document_entities(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Esegue (o ri-esegue) l'estrazione strutturata di entità tramite LangExtract
    sul testo OCR già memorizzato del documento indicato.

    Le entità vengono salvate in DocumentMetadata.metadata_json e restituite
    nella risposta. L'utente deve essere proprietario o ADMIN.
    """
    from ..services.langextract_service import extract_entities, entities_to_metadata_patch
    from ..models.user import UserRole

    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Integrazione Gemini/LangExtract non configurata.",
        )

    # Recupera documento e verifica accesso
    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    # Recupera il testo OCR
    content_stmt = select(DocumentContent).where(DocumentContent.document_id == doc_id)
    content_row = (await db.execute(content_stmt)).scalar_one_or_none()
    ocr_text = (content_row.fulltext_content or "") if content_row else ""

    if not ocr_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Nessun testo disponibile per l'estrazione (OCR non ancora completato?).",
        )

    # Esegui LangExtract
    entities = await extract_entities(ocr_text, api_key=settings.GEMINI_API_KEY)
    patch = entities_to_metadata_patch(entities)

    # Persisti in metadata_json
    meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id)
    meta = (await db.execute(meta_stmt)).scalar_one_or_none()
    if meta:
        current_json = dict(meta.metadata_json or {})
        for key in ("extracted_entities", "doc_type", "parties", "dates", "amounts", "references"):
            value = patch.get(key)
            if value:
                current_json[key] = value
        meta.metadata_json = current_json
        await db.commit()

    return ExtractEntitiesResponse(
        document_id=str(doc_id),
        entity_count=len(entities),
        doc_type=patch.get("doc_type"),
        parties=patch.get("parties", []),
        dates=patch.get("dates", []),
        amounts=patch.get("amounts", []),
        references=patch.get("references", []),
        extracted_entities=entities,
    )


# ── Smart Folder Suggestion ───────────────────────────────────────────────────

@router.get("/suggest-folder/{doc_id}")
async def suggest_folder_for_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analizza il contenuto del documento e suggerisce la cartella più appropriata
    tra quelle create dall'utente.

    Returns:
        {folder_id, folder_name, confidence (0-1), reason}
        oppure {folder_id: null, folder_name: null, reason: '...'} se nessuna cartella adatta.
    """
    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini non configurato.")

    # Verifica accesso documento
    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")

    # Recupera testo OCR
    content_stmt = select(DocumentContent).where(DocumentContent.document_id == doc_id)
    content_row = (await db.execute(content_stmt)).scalar_one_or_none()
    ocr_text = ((content_row.fulltext_content or "") if content_row else "")[:4000]

    if not ocr_text.strip():
        raise HTTPException(status_code=422, detail="Nessun testo disponibile (OCR non ancora completato).")

    # Recupera cartelle dell'utente
    folders_stmt = select(Folder).where(Folder.owner_id == current_user.id)
    folders = (await db.execute(folders_stmt)).scalars().all()

    if not folders:
        return {"folder_id": None, "folder_name": None, "confidence": 0.0, "reason": "Nessuna cartella disponibile."}

    folder_list = "\n".join(f"- ID: {f.id} | Nome: {f.name}" for f in folders)

    prompt = f"""Sei un assistente di archiviazione documentale aziendale.

Analizza il testo del documento e scegli la cartella più appropriata tra quelle elencate.

CARTELLE DISPONIBILI:
{folder_list}

TITOLO DOCUMENTO: {doc.title}

TESTO DOCUMENTO (estratto):
{ocr_text}

Rispondi SOLO con un JSON nel formato:
{{"folder_id": "<UUID della cartella scelta>", "folder_name": "<nome cartella>", "confidence": <numero 0-1>, "reason": "<breve motivazione>"}}

Se nessuna cartella è adatta, usa:
{{"folder_id": null, "folder_name": null, "confidence": 0, "reason": "<perché nessuna è adatta>"}}
"""

    import json as _json

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-1.5-flash")

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        raw = (response.text or "{}").strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:])
            raw = raw.rsplit("```", 1)[0].strip()
        result = _json.loads(raw)

        # Valida che folder_id sia tra le cartelle dell'utente
        valid_ids = {str(f.id) for f in folders}
        if result.get("folder_id") and result["folder_id"] not in valid_ids:
            result["folder_id"] = None
            result["folder_name"] = None
            result["confidence"] = 0.0

        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Errore Gemini: {exc}")
