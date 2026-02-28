from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, update as sa_update
import google.generativeai as genai
from uuid import UUID

from ..db import get_db
from ..models.user import User
from ..models.document import Document, DocumentContent, DocumentMetadata
from ..api.auth import get_current_user
from ..schemas.ai_schemas import (
    ChatQueryRequest, ChatResponse, ChatSource,
    ExtractEntitiesResponse, PageIndexResponse,
    AnalysisResponse, SimilarDocumentsResponse,
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

    # Collect document IDs to fetch PageIndex trees for targeted queries
    result_doc_ids = [str(row[1]) for row in rows]

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

    # 3b. If a specific document was targeted, enrich context with its
    #     PageIndex tree (structured section summaries — PageIndex approach).
    tree_context = ""
    if request.document_id:
        from ..models.document import DocumentMetadata
        from ..services.pageindex_service import tree_to_rag_context

        meta_stmt = select(DocumentMetadata).where(
            DocumentMetadata.document_id == request.document_id
        )
        meta_row = (await db.execute(meta_stmt)).scalar_one_or_none()
        if meta_row:
            page_index = (meta_row.metadata_json or {}).get("page_index", {})
            tree_context = tree_to_rag_context(page_index)

    # 4. prompt Gemini con Retrieval-Augmented Generation
    structure_block = (
        f"\nSTRUTTURA DEL DOCUMENTO (indice gerarchico):\n{tree_context}\n"
        if tree_context
        else ""
    )
    prompt = f"""
Sei un assistente aziendale intelligente e professionale. Rispondi alla domanda dell'utente basandoti ESCLUSIVAMENTE sul seguente contesto estratto dai documenti aziendali.
{structure_block}
CONTESTO:
{context_text}

DOMANDA UTENTE: {request.query}

ISTRUZIONI:
- Rispondi in italiano in modo chiaro, conciso e diretto.
- Se la risposta non è presente nel contesto, dichiara apertamente che non hai informazioni sufficienti nei documenti forniti, e NON inventare nulla.
- Cita sempre le fonti (es. "In base al documento X...").
- Se è disponibile una struttura gerarchica, usala per localizzare con precisione la sezione rilevante.
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


# ── PageIndex: on-demand hierarchical tree indexing ───────────────────────────

@router.post("/pageindex/{doc_id}", response_model=PageIndexResponse)
async def index_document_pages(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Build (or rebuild) the PageIndex hierarchical tree for a PDF document.

    Inspired by https://github.com/VectifyAI/PageIndex — replaces flat
    vector chunks with a TOC-driven tree of sections and AI summaries that
    lets /ai/chat reason about document structure rather than similarity.

    The result is stored in DocumentMetadata.metadata_json["page_index"]
    and returned in the response.  Only PDF documents are supported.
    Owner or ADMIN required.
    """
    from ..services.pageindex_service import build_page_index, tree_to_rag_context
    from ..models.user import UserRole
    from ..core.storage import LocalStorage

    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Gemini non configurato — necessario per PageIndex.",
        )

    # Recupera documento e verifica accesso
    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")
    if doc.file_type != "application/pdf":
        raise HTTPException(
            status_code=422,
            detail="PageIndex è supportato solo per documenti PDF.",
        )

    # Recupera il percorso fisico del file dall'ultima versione
    from ..models.document import DocumentVersion
    ver_stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    )
    version = (await db.execute(ver_stmt)).scalars().first()
    if not version:
        raise HTTPException(status_code=404, detail="Nessuna versione trovata per il documento.")

    storage = LocalStorage()
    abs_path = await storage.get_file_path(version.file_path)

    # Esegui PageIndex
    page_index = await build_page_index(
        pdf_path=abs_path,
        doc_title=doc.title,
        api_key=settings.GEMINI_API_KEY,
    )

    if not page_index:
        raise HTTPException(
            status_code=500,
            detail="Impossibile costruire l'indice gerarchico per questo documento.",
        )

    # Persisti in metadata_json
    meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id)
    meta = (await db.execute(meta_stmt)).scalar_one_or_none()
    if meta:
        current_json = dict(meta.metadata_json or {})
        current_json["page_index"] = page_index
        meta.metadata_json = current_json
        await db.commit()

    from ..services.pageindex_service import _flatten_tree

    return PageIndexResponse(
        document_id=str(doc_id),
        total_pages=page_index.get("total_pages", 0),
        section_count=len(_flatten_tree(page_index.get("children", []))),
        page_index=page_index,
    )


# ── Deep document analysis ────────────────────────────────────────────────────

@router.post("/analyze/{doc_id}", response_model=AnalysisResponse)
async def analyze_document_endpoint(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run (or re-run) deep analysis on a document:
    classification · relationships · risk indicators · timeline ·
    multi-level summary.

    Results are persisted in DocumentMetadata.metadata_json["analysis"]
    and returned in the response. Owner or ADMIN only.
    """
    from ..services.document_analyzer import (
        analyze_document, analysis_to_dict, get_risk_summary,
    )
    from ..models.user import UserRole

    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini non configurato.")

    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    content_stmt = select(DocumentContent).where(DocumentContent.document_id == doc_id)
    content_row = (await db.execute(content_stmt)).scalar_one_or_none()
    ocr_text = (content_row.fulltext_content or "") if content_row else ""

    if not ocr_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Nessun testo disponibile (OCR non ancora completato?).",
        )

    # Retrieve pre-extracted entities as hint
    meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id)
    meta = (await db.execute(meta_stmt)).scalar_one_or_none()
    entities = []
    if meta:
        entities = (meta.metadata_json or {}).get("extracted_entities", [])

    analysis = await analyze_document(
        text=ocr_text,
        title=doc.title,
        api_key=settings.GEMINI_API_KEY,
        entities=entities,
    )
    if not analysis:
        raise HTTPException(status_code=500, detail="Analisi fallita.")

    analysis_dict = analysis_to_dict(analysis)
    risk_summary = get_risk_summary(analysis)

    # Persist
    if meta:
        current_json = dict(meta.metadata_json or {})
        current_json["analysis"] = analysis_dict
        current_json["risk_summary"] = risk_summary
        # Promote classification to top-level for easy filtering
        current_json["primary_category"] = analysis.classification.primary_category
        current_json["doc_type_analyzed"] = analysis.classification.doc_type
        meta.metadata_json = current_json
        await db.commit()

    from ..schemas.ai_schemas import (
        ClassificationOut, RelationshipOut, RiskIndicatorOut,
        TimelineEventOut, AnalysisResponse,
    )

    return AnalysisResponse(
        document_id=str(doc_id),
        classification=ClassificationOut(**analysis_to_dict(analysis)["classification"]),
        relationships=[RelationshipOut(**r) for r in analysis_to_dict(analysis)["relationships"]],
        risk_indicators=[RiskIndicatorOut(**r) for r in analysis_to_dict(analysis)["risk_indicators"]],
        timeline=[TimelineEventOut(**e) for e in analysis_to_dict(analysis)["timeline"]],
        executive_summary=analysis.executive_summary,
        key_points=analysis.key_points,
        detailed_summary=analysis.detailed_summary,
        risk_summary=risk_summary,
        analysis_version=analysis.analysis_version,
        analyzed_at=analysis.analyzed_at,
    )


@router.get("/analyze/{doc_id}", response_model=AnalysisResponse)
async def get_analysis(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the last stored analysis for a document (no re-computation)."""
    from ..models.user import UserRole
    from ..schemas.ai_schemas import (
        ClassificationOut, RelationshipOut, RiskIndicatorOut,
        TimelineEventOut, AnalysisResponse,
    )

    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id)
    meta = (await db.execute(meta_stmt)).scalar_one_or_none()
    analysis_dict = (meta.metadata_json or {}).get("analysis") if meta else None

    if not analysis_dict:
        raise HTTPException(
            status_code=404,
            detail="Nessuna analisi disponibile. Esegui prima POST /ai/analyze/{doc_id}.",
        )

    risk_summary = (meta.metadata_json or {}).get("risk_summary", {})

    return AnalysisResponse(
        document_id=str(doc_id),
        classification=ClassificationOut(**analysis_dict["classification"]),
        relationships=[RelationshipOut(**r) for r in analysis_dict.get("relationships", [])],
        risk_indicators=[RiskIndicatorOut(**r) for r in analysis_dict.get("risk_indicators", [])],
        timeline=[TimelineEventOut(**e) for e in analysis_dict.get("timeline", [])],
        executive_summary=analysis_dict.get("executive_summary", ""),
        key_points=analysis_dict.get("key_points", []),
        detailed_summary=analysis_dict.get("detailed_summary", ""),
        risk_summary=risk_summary,
        analysis_version=analysis_dict.get("analysis_version", "1.0"),
        analyzed_at=analysis_dict.get("analyzed_at", ""),
    )


# ── Similar documents ─────────────────────────────────────────────────────────

@router.get("/similar/{doc_id}", response_model=SimilarDocumentsResponse)
async def find_similar_documents(
    doc_id: UUID,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Find documents semantically similar to *doc_id* using pgvector
    cosine distance on the 768-dim Gemini embeddings.

    Returns up to *limit* similar documents (excluding the source doc itself).
    Restricted documents not shared with the requesting user are excluded.
    """
    from ..schemas.ai_schemas import SimilarDocumentOut, SimilarDocumentsResponse
    from ..models.user import UserRole

    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")

    # Fetch the embedding of the source document
    emb_stmt = select(DocumentContent).where(DocumentContent.document_id == doc_id)
    src_content = (await db.execute(emb_stmt)).scalar_one_or_none()
    if not src_content or src_content.embedding is None:
        raise HTTPException(
            status_code=422,
            detail="Embedding non disponibile per questo documento.",
        )

    embedding_str = str(list(src_content.embedding))

    stmt = text("""
        SELECT d.id, d.title, d.is_restricted,
               (c.embedding <=> :emb::vector) AS distance,
               m.metadata_json
        FROM doc_content c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN doc_metadata m ON m.document_id = d.id
        WHERE d.is_deleted = false
          AND d.id != :src_id
          AND c.embedding IS NOT NULL
          AND (d.owner_id = :user_id OR d.is_restricted = false
               OR :is_admin = true)
        ORDER BY distance ASC
        LIMIT :lim
    """)

    rows = (await db.execute(stmt, {
        "emb": embedding_str,
        "src_id": str(doc_id),
        "user_id": str(current_user.id),
        "is_admin": current_user.role == UserRole.ADMIN,
        "lim": min(limit, 20),
    })).fetchall()

    similar = []
    for row in rows:
        meta_json = row[4] or {}
        analysis = meta_json.get("analysis", {})
        cls = analysis.get("classification", {})
        similar.append(SimilarDocumentOut(
            document_id=str(row[0]),
            title=row[1],
            similarity=round(1.0 - float(row[3]), 4),
            primary_category=cls.get("primary_category"),
            doc_type=cls.get("doc_type"),
        ))

    return SimilarDocumentsResponse(document_id=str(doc_id), similar=similar)
