from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, update as sa_update, and_, or_, cast
from pgvector.sqlalchemy import Vector
import google.generativeai as genai
from uuid import UUID

from ..db import get_db
from ..models.user import User
from ..models.document import Document, DocumentContent, DocumentMetadata
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

    # 2. Cerca nel database con pgvector usando l'ORM per il corretto cast vettoriale
    stmt = (
        select(
            DocumentContent.document_id,
            DocumentContent.fulltext_content,
            Document.title,
            Document.is_restricted,
            DocumentContent.embedding.cosine_distance(cast(query_embedding, Vector)).label("distance")
        )
        .join(Document, DocumentContent.document_id == Document.id)
        .where(
            Document.is_deleted == False,
            DocumentContent.embedding.isnot(None),
            or_(Document.owner_id == current_user.id, Document.is_restricted == False)
        )
    )

    # Se document_id è specificato, confina la ricerca
    if request.document_id:
        stmt = stmt.where(Document.id == request.document_id)

    # Ordina per similarità (distanza coseno minore = più simile) e limita
    stmt = stmt.order_by("distance").limit(5)

    try:
        results = await db.execute(stmt)
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
        # row: document_id, fulltext_content, title, is_restricted, distance
        doc_id = str(row[0])
        fulltext = row[1] or ""
        title = row[2]
        
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
