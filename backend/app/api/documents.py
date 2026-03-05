import asyncio
import json
import hashlib
import logging
import mimetypes
import os
import aiofiles
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sa_update, delete as sa_delete, or_, and_, distinct, func, cast
from sqlalchemy.orm import selectinload
import asyncio
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from ..db import get_db, SessionLocal
from ..models.user import User, UserRole
from ..models.document import Document, DocumentVersion, DocumentMetadata, DocumentContent, DocumentShare
from ..models.audit import AuditLog
from pgvector.sqlalchemy import Vector
from ..schemas.doc_schemas import (
    DocumentResponse, DocumentCreate, DocumentVersionResponse, PaginatedDocuments,
    DocumentUpdate, BulkExportRequest, BulkDeleteRequest, DocumentShareCreate, DocumentShareResponse,
)
from ..api.auth import get_current_user
from ..api.ws import manager
from ..core.storage import get_storage, StorageLayer, LocalStorage
from ..core.cache import get_redis
from ..core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

_CACHE_TTL = 300  # secondi


# ── Helper: verifica accesso ──────────────────────────────────────────────────

async def _get_accessible_doc(doc_id: UUID, current_user: User, db: AsyncSession) -> Document:
    """
    Ritorna il documento se l'utente ha accesso.
    Regole: proprietario | ADMIN | condivisione esplicita | documento pubblico non cancellato.
    """
    stmt = (
        select(Document)
        .options(selectinload(Document.metadata_entries), selectinload(Document.owner))
        .where(Document.id == doc_id, Document.is_deleted == False)
    )
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")

    if current_user.role == UserRole.ADMIN or doc.owner_id == current_user.id:
        return doc

    if not doc.is_restricted:
        return doc

    # Documento riservato: verifica condivisione esplicita
    share_stmt = select(DocumentShare).where(
        DocumentShare.document_id == doc_id,
        DocumentShare.shared_with_id == current_user.id,
    )
    if not (await db.execute(share_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Accesso negato.")
    return doc


async def _invalidate_user_cache(redis, user_id: UUID) -> None:
    if not redis:
        return
    try:
        async for key in redis.scan_iter(f"docs:{user_id}:*"):
            await redis.delete(key)
    except Exception:
        pass


# ── Background: OCR + Gemini tagging ─────────────────────────────────────────

async def _run_ocr_background(
    doc_id: UUID,
    file_rel_path: str,
    content_type: str,
    initial_corpus: str,
    run_llm: bool = True,
) -> None:
    """
    Eseguito dopo la risposta HTTP: estrae il testo dal file via OCR
    e aggiorna DocumentContent.fulltext_content. Se run_llm è True, analizza con Gemini
    e lancia LangExtract per l'estrazione strutturata di entità.
    """
    from ..services.ocr import extract_text
    from ..services.llm_metadata import extract_metadata_from_text
    from ..services.embeddings import generate_embedding
    from ..services.langextract_service import extract_entities, entities_to_metadata_patch
    from ..core.config import settings

    storage = LocalStorage()
    abs_path = await storage.get_file_path(file_rel_path)

    ocr_text = await extract_text(abs_path, content_type)
    merged = f"{initial_corpus} {ocr_text}".strip() if ocr_text else initial_corpus

    merged = f"{initial_corpus} {ocr_text}".strip()

    ai_metadata = None
    ai_embedding = None
    entity_patch = {}
    if run_llm:
        # Run basic metadata extraction and LangExtract entity extraction concurrently
        ai_metadata_task = asyncio.create_task(extract_metadata_from_text(merged))
        embedding_task = asyncio.create_task(generate_embedding(merged))

        # LangExtract structured extraction (requires Gemini API key)
        entities_task = None
        if settings.GEMINI_ENABLED and settings.GEMINI_API_KEY:
            entities_task = asyncio.create_task(
                extract_entities(merged, api_key=settings.GEMINI_API_KEY)
            )

        ai_metadata = await ai_metadata_task
        ai_embedding = await embedding_task
        if entities_task is not None:
            entities = await entities_task
            if entities:
                entity_patch = entities_to_metadata_patch(entities)
                logger.info(
                    "LangExtract: %d entità estratte per documento %s.", len(entities), doc_id
                )

    async with SessionLocal() as db:
        try:
            update_values = {"fulltext_content": merged}
            if ai_embedding is not None:
                update_values["embedding"] = ai_embedding

            stmt = (
                sa_update(DocumentContent)
                .where(DocumentContent.document_id == doc_id)
                .values(**update_values)
            )
            await db.execute(stmt)

            if ai_metadata or entity_patch:
                # 1. Update Document department
                doc_stmt = select(Document).where(Document.id == doc_id)
                doc = (await db.execute(doc_stmt)).scalar_one_or_none()
                if doc:
                    if not doc.department and ai_metadata and ai_metadata.get("department") and ai_metadata["department"] != "Generale":
                        doc.department = ai_metadata["department"]
                    
                    # 2. Update DocumentVersion AI Summary & Status
                    if doc.current_version_id:
                        from ..models.document import DocumentVersion, Tag, DocumentVersionTag
                        ver_stmt = select(DocumentVersion).where(DocumentVersion.id == doc.current_version_id)
                        ver = (await db.execute(ver_stmt)).scalar_one_or_none()
                        if ver:
                            ver.ai_status = "ready"
                            if ai_metadata and ai_metadata.get("summary"):
                                ver.ai_summary = ai_metadata["summary"]
                            
                            # 3. Add auto-tags into DocumentVersionTag
                            if ai_metadata and ai_metadata.get("tags"):
                                for tag_name in ai_metadata["tags"]:
                                    tag_name_clean = str(tag_name).strip().lower()
                                    if not tag_name_clean: continue
                                    
                                    # Find or create Tag
                                    tag_q = select(Tag).where(Tag.name == tag_name_clean)
                                    existing_tag = (await db.execute(tag_q)).scalar_one_or_none()
                                    if not existing_tag:
                                        existing_tag = Tag(name=tag_name_clean)
                                        db.add(existing_tag)
                                        await db.flush()
                                        
                                    # Check if link exists
                                    link_q = select(DocumentVersionTag).where(
                                        DocumentVersionTag.document_version_id == ver.id,
                                        DocumentVersionTag.tag_id == existing_tag.id
                                    )
                                    if not (await db.execute(link_q)).scalar_one_or_none():
                                        db.add(DocumentVersionTag(
                                            document_version_id=ver.id,
                                            tag_id=existing_tag.id,
                                            is_ai_generated=True
                                        ))

                # Update structured legacy metadata block
                meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id)
                meta = (await db.execute(meta_stmt)).scalar_one_or_none()
                if meta:
                    current_json = meta.metadata_json or {}

                    if ai_metadata:
                        existing_tags = set(current_json.get("tags", []))
                        ai_tags = set(ai_metadata.get("tags", []))
                        current_json["tags"] = list(existing_tags.union(ai_tags))

                        if not current_json.get("dept") and ai_metadata.get("department"):
                            if ai_metadata["department"] != "Generale":
                                current_json["dept"] = ai_metadata["department"]

                    # Merge LangExtract structured entities into metadata
                    if entity_patch:
                        for key in ("extracted_entities", "doc_type", "parties",
                                    "dates", "amounts", "references"):
                            value = entity_patch.get(key)
                            if value:
                                current_json[key] = value

                    meta.metadata_json = dict(current_json)

            await db.commit()
            logger.info("OCR/LLM completata per documento %s (%d chars).", doc_id, len(merged))

            # Notifica completamento al Frontend
            # Ottieni info minime per la UI (il doc_id ci e' noto)
            owner_stmt = select(Document).where(Document.id == doc_id)
            doc_info = (await db.execute(owner_stmt)).scalar_one_or_none()
            if doc_info:
                await manager.send_personal_message(
                    {
                        "type": "UPLOAD_COMPLETE",
                        "message": f"Caricamento OCR ed elaborazione AI del documento '{doc_info.title}' completati correttamente.",
                        "doc_id": str(doc_id)
                    },
                    doc_info.owner_id
                )

        except Exception as exc:
            await db.rollback()
            logger.warning("Background OCR/tag fallito per %s: %s", doc_id, exc)


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse)
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    is_restricted: bool = Form(False),
    metadata_json: str = Form("{}"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
    redis=Depends(get_redis),
):
    allowed_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo file non consentito.")

    try:
        metadata_data = json.loads(metadata_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="metadata_json non è JSON valido.")

    file_rel_path = await storage.save_file(file.file, file.filename)

    doc = Document(
        title=title,
        owner_id=current_user.id,
        is_restricted=is_restricted,
        file_type=file.content_type,
        department=current_user.department,
    )
    db.add(doc)
    await db.flush()

    ver = DocumentVersion(document_id=doc.id, version_num=1, file_path=file_rel_path, ai_status="processing")
    db.add(ver)
    await db.flush()
    
    doc.current_version_id = ver.id

    db.add(DocumentMetadata(document_id=doc.id, metadata_json=metadata_data))

    tags_text = " ".join(metadata_data.get("tags", []))
    author_text = metadata_data.get("author", "")
    dept_text = metadata_data.get("dept", "")
    initial_corpus = " ".join(filter(None, [title, author_text, dept_text, tags_text]))
    db.add(DocumentContent(document_id=doc.id, fulltext_content=initial_corpus))
    
    from ..models.audit import AuditLog
    db.add(AuditLog(user_id=current_user.id, action="UPLOAD", target_id=doc.id, document_version_id=ver.id))

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.exception("Commit fallito per caricamento documento %s", title)
        raise HTTPException(status_code=500, detail=f"Errore salvataggio database: {str(exc)}")

    background_tasks.add_task(
        _run_ocr_background, doc.id, file_rel_path, file.content_type, initial_corpus
    )
    await _invalidate_user_cache(redis, current_user.id)

    # Re-fetch with selectinload to avoid MissingGreenlet in schemas/responses
    # DocumentResponse/doc_metadata depends on metadata_entries, owner, content, and versions
    stmt = (
        select(Document)
        .options(
            selectinload(Document.metadata_entries),
            selectinload(Document.owner),
            selectinload(Document.content),
            selectinload(Document.versions)
        )
        .where(Document.id == doc.id)
    )
    doc_final = (await db.execute(stmt)).scalar_one()
    return doc_final


# ── Nuova Versione ────────────────────────────────────────────────────────────

@router.post("/{doc_id}/versions", response_model=DocumentResponse)
@limiter.limit("20/minute")
async def upload_document_version(
    doc_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
    redis=Depends(get_redis),
):
    stmt = select(Document).options(selectinload(Document.metadata_entries)).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(stmt)).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or in trash")

    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    allowed_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo file non consentito.")

    file_rel_path = await storage.save_file(file.file, file.filename)
    
    doc.current_version += 1
    doc.file_type = file.content_type
    
    db.add(DocumentVersion(document_id=doc.id, version_num=doc.current_version, file_path=file_rel_path))
    
    if doc.metadata_entries:
        metadata_data = doc.metadata_entries[0].metadata_json
    else:
        metadata_data = {}

    tags_text = " ".join(metadata_data.get("tags", []))
    author_text = metadata_data.get("author", "")
    dept_text = metadata_data.get("dept", "")
    initial_corpus = " ".join(filter(None, [doc.title, author_text, dept_text, tags_text]))
    
    db.add(AuditLog(user_id=current_user.id, action="NEW_VERSION", target_id=doc.id))
    
    await db.commit()

    # Notifica di caricamento nuova versione all'owner se a farlo è stato un admin
    if doc.owner_id != current_user.id:
        await manager.send_personal_message(
            {
                "type": "DOC_MODIFIED",
                "message": f"Una nuova versione del documento '{doc.title}' e' stata caricata da {current_user.email}.",
                "doc_id": str(doc.id)
            },
            doc.owner_id
        )

    background_tasks.add_task(
        _run_ocr_background, doc.id, file_rel_path, file.content_type, initial_corpus
    )
    await _invalidate_user_cache(redis, current_user.id)
    
    # Re-fetch with all relationships
    stmt = (
        select(Document)
        .options(
            selectinload(Document.metadata_entries),
            selectinload(Document.owner),
            selectinload(Document.content),
            selectinload(Document.versions)
        )
        .where(Document.id == doc.id)
    )
    doc_final = (await db.execute(stmt)).scalar_one()
    return doc_final


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: UUID,
    update_data: DocumentUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    stmt = select(Document).options(selectinload(Document.metadata_entries)).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(stmt)).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or in trash")

    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Update base fields
    if update_data.title is not None:
        doc.title = update_data.title
    if update_data.is_restricted is not None:
        doc.is_restricted = update_data.is_restricted

    # Update metadata
    if update_data.doc_metadata is not None:
        if doc.metadata_entries:
            doc.metadata_entries[0].metadata_json = update_data.doc_metadata
        else:
            new_meta = DocumentMetadata(document_id=doc.id, metadata_json=update_data.doc_metadata)
            db.add(new_meta)

    # Recompute base corpus for FTS if title or metadata changed
    if update_data.title is not None or update_data.doc_metadata is not None:
        meta_dict = update_data.doc_metadata if update_data.doc_metadata is not None else (doc.metadata_entries[0].metadata_json if doc.metadata_entries else {})
        tags_text = " ".join(meta_dict.get("tags", []))
        author_text = meta_dict.get("author", "")
        dept_text = meta_dict.get("dept", "")
        
        initial_corpus = " ".join(filter(None, [doc.title, author_text, dept_text, tags_text]))
        
        # We need the file_path to rerun OCR
        v_stmt = select(DocumentVersion).where(DocumentVersion.document_id == doc_id, DocumentVersion.version_num == doc.current_version)
        ver = (await db.execute(v_stmt)).scalar_one_or_none()
        
        if ver:
            # We must schedule OCR again so it appends to the new initial corpus, 
            # because previous OCR text is mixed into the DB row and we can't easily extract it.
            # Rerunning OCR ensures consistency.
            import mimetypes
            # Try to guess mime type from file path
            mime_type, _ = mimetypes.guess_type(ver.file_path)
            mime_type = mime_type or "application/octet-stream"
            
            background_tasks.add_task(
                _run_ocr_background,
                doc.id,
                ver.file_path,
                mime_type,
                initial_corpus,
                run_llm=False
            )
            
            # Temporary set the corpus to just the metadata until OCR finishes, or just wait.
            # The background task will OVERWRITE the DocumentContent.fulltext_content.

    # Audit log
    audit = AuditLog(user_id=current_user.id, action="UPDATE", target_id=doc.id)
    db.add(audit)

    await db.commit()

    # Re-fetch with all relationships to avoid MissingGreenlet in schemas/responses
    stmt = (
        select(Document)
        .options(
            selectinload(Document.metadata_entries),
            selectinload(Document.owner),
            selectinload(Document.content),
            selectinload(Document.versions)
        )
        .where(Document.id == doc.id)
    )
    doc_final = (await db.execute(stmt)).scalar_one()

    # Notifica modifica se eseguita da un altro utente diverso dal proprietario
    if doc_final.owner_id != current_user.id:
        await manager.send_personal_message(
            {
                "type": "DOC_MODIFIED",
                "message": f"Il documento '{doc_final.title}' e' stato aggiornato da {current_user.email}.",
                "doc_id": str(doc_final.id)
            },
            doc_final.owner_id
        )

    # Invalidate search cache
    if redis:
        try:
            async for key in redis.scan_iter(f"docs:{current_user.id}:*"):
                await redis.delete(key)
        except Exception:
            pass

    return doc_final


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=PaginatedDocuments)
@limiter.limit("120/minute")
async def search_documents(
    request: Request,
    query: Optional[str] = Query(None, max_length=200),
    tag: Optional[str] = None,
    file_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    author: Optional[str] = None,
    department: Optional[str] = None,
    mode: Optional[str] = Query(None, description="'semantic' per ricerca solo vettoriale"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache_key = (
        f"docs:{current_user.id}:"
        + hashlib.md5(
            f"{query}:{tag}:{file_type}:{date_from}:{date_to}:{author}:{department}:{mode}:{limit}:{offset}".encode()
        ).hexdigest()
    )
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    filters = [Document.is_deleted == False]
    need_content_join = False
    need_meta_join = False

    # RBAC: ADMIN vede tutto; gli altri vedono propri + pubblici + condivisi
    if current_user.role != UserRole.ADMIN:
        shared_ids = (
            select(DocumentShare.document_id)
            .where(DocumentShare.shared_with_id == current_user.id)
            .scalar_subquery()
        )
        filters.append(
            or_(
                Document.is_restricted == False,
                Document.owner_id == current_user.id,
                Document.id.in_(shared_ids),
            )
        )

    if query:
        need_content_join = True

        # Genera embedding per la query
        from ..services.embeddings import generate_query_embedding
        query_emb = await generate_query_embedding(query)

        if mode == "semantic":
            # Ricerca SOLO vettoriale — nessun FTS
            if query_emb:
                semantic_condition = DocumentContent.embedding.cosine_distance(cast(query_emb, Vector)) < 0.70
                filters.append(semantic_condition)
            else:
                # Fallback a titolo se embedding non disponibile
                filters.append(Document.title.ilike(f"%{query}%"))
        else:
            # Modalità ibrida (default): FTS + vettoriale + titolo
            fts_condition = and_(
                DocumentContent.search_vector.isnot(None),
                DocumentContent.search_vector.op("@@")(func.plainto_tsquery("italian", query)),
            )

            if query_emb:
                semantic_condition = DocumentContent.embedding.cosine_distance(cast(query_emb, Vector)) < 0.65
                filters.append(or_(fts_condition, Document.title.ilike(f"%{query}%"), semantic_condition))
            else:
                filters.append(or_(fts_condition, Document.title.ilike(f"%{query}%")))


    if tag:
        need_meta_join = True
        filters.append(DocumentMetadata.metadata_json["tags"].contains([tag]))

    if file_type:
        filters.append(Document.file_type == file_type)

    if date_from:
        filters.append(Document.created_at >= date_from)

    if date_to:
        filters.append(Document.created_at <= date_to)

    if author:
        need_meta_join = True
        filters.append(DocumentMetadata.metadata_json["author"].astext.ilike(f"%{author}%"))

    if department:
        need_meta_join = True
        filters.append(DocumentMetadata.metadata_json["dept"].astext == department)

    count_stmt = select(func.count(distinct(Document.id))).select_from(Document)
    if need_content_join:
        count_stmt = count_stmt.outerjoin(Document.content)
    if need_meta_join:
        count_stmt = count_stmt.outerjoin(Document.metadata_entries)
    count_stmt = count_stmt.where(*filters)
    total: int = (await db.execute(count_stmt)).scalar() or 0

    # Definiamo cosa estrarre. Di base estraiamo solo l'oggetto Document
    query_cols = [Document]
    order_by_col = Document.created_at.desc()
    
    # Ordina per rilevanza semantica se c'è una query
    if query:
        # Prepariamo l'espressione ts_headline
        ts_headline_expr = func.ts_headline(
            'italian',
            DocumentContent.fulltext_content,
            func.plainto_tsquery('italian', query),
            'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
        )
        query_cols.append(ts_headline_expr.label('snippet'))
            
        if 'query_emb' in locals() and query_emb:
            dist_expr = DocumentContent.embedding.cosine_distance(cast(query_emb, Vector))
            query_cols.append(dist_expr.label('distance'))
            order_by_col = dist_expr.asc()
        else:
            order_by_col = Document.created_at.desc()

    stmt = select(*query_cols).options(
        selectinload(Document.metadata_entries),
        selectinload(Document.owner),
        selectinload(Document.content)
    ).order_by(order_by_col)
    
    if need_content_join:
        stmt = stmt.outerjoin(Document.content)
    if need_meta_join:
        stmt = stmt.outerjoin(Document.metadata_entries)
    if filters:
        stmt = stmt.where(*filters)

    stmt = stmt.offset(offset).limit(limit)

    results = (await db.execute(stmt)).unique().all()

    # Bulk-fetch is_indexed status for returned docs
    doc_ids_in_page = [row[0].id for row in results]
    indexed_ids: set = set()
    if doc_ids_in_page:
        indexed_stmt = (
            select(DocumentContent.document_id)
            .where(
                DocumentContent.document_id.in_(doc_ids_in_page),
                DocumentContent.embedding.isnot(None),
            )
        )
        indexed_rows = (await db.execute(indexed_stmt)).scalars().all()
        indexed_ids = {row for row in indexed_rows}

    parsed_items = []
    for row in results:
        doc_obj = row[0]
        snippet = getattr(row, 'snippet', None)
        distance = getattr(row, 'distance', None)
        
        # Fallback snippet if ts_headline failed (common in semantic-only matches)
        if not snippet and doc_obj.content:
            text = doc_obj.content.fulltext_content or ""
            # Simple keyword match for fallback snippet
            idx = text.lower().find((query or "").lower())
            if idx != -1:
                start = max(0, idx - 50)
                snippet = "..." + text[start:start+200] + "..."
            else:
                snippet = text[:200] + ("..." if len(text) > 200 else "")

        # Relevance Score Calculate
        relevance_score = None
        if distance is not None:
            # Cosine distance typically between 0 (identical) and 2 (opposite).
            # We map 0 -> 100%, 1.0 -> 0%
            score = max(0.0, min(100.0, (1.0 - distance) * 100.0))
            relevance_score = round(score, 1)

        setattr(doc_obj, 'highlight_snippet', snippet)
        setattr(doc_obj, 'is_indexed', doc_obj.id in indexed_ids)
        setattr(doc_obj, 'relevance_score', relevance_score)
        parsed_items.append(DocumentResponse.model_validate(doc_obj))

    response = PaginatedDocuments(
        items=parsed_items,
        total=total,
        limit=limit,
        offset=offset,
    )

    if redis:
        try:
            await redis.setex(cache_key, _CACHE_TTL, json.dumps(response.model_dump(mode="json")))
        except Exception:
            pass

    return response


# ── Related Documents ────────────────────────────────────────────────────────

@router.get("/{doc_id}/related", response_model=list[DocumentResponse])
@limiter.limit("60/minute")
async def get_related_documents(
    doc_id: UUID,
    request: Request,
    limit: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Retrieve the source document's embedding
    stmt = select(DocumentContent).where(DocumentContent.document_id == doc_id)
    source_content = (await db.execute(stmt)).scalar_one_or_none()
    
    if not source_content or source_content.embedding is None:
        return []
        
    filters = [
        Document.id != doc_id,
        Document.is_deleted == False
    ]
    
    # RBAC filtering
    if current_user.role != UserRole.ADMIN:
        shared_ids = (
            select(DocumentShare.document_id)
            .where(DocumentShare.shared_with_id == current_user.id)
            .scalar_subquery()
        )
        filters.append(
            or_(
                Document.is_restricted == False,
                Document.owner_id == current_user.id,
                Document.id.in_(shared_ids),
            )
        )
        
    # Similarity query
    stmt = (
        select(Document)
        .join(DocumentContent)
        .options(
            selectinload(Document.metadata_entries),
            selectinload(Document.owner),
            selectinload(Document.content),
            selectinload(Document.versions)
        )
        .where(
            *filters,
            DocumentContent.embedding.cosine_distance(source_content.embedding) < 0.65
        )
        .order_by(DocumentContent.embedding.cosine_distance(source_content.embedding))
        .limit(limit)
    )
    
    related_docs = list((await db.execute(stmt)).scalars().unique().all())
    return [DocumentResponse.model_validate(d) for d in related_docs]


# ── Export Bulk (ZIP) ─────────────────────────────────────────────────────────

@router.post("/export-bulk")
async def export_bulk_documents(
    request: BulkExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
):
    if not request.document_ids:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    stmt = select(Document).options(
        selectinload(Document.owner),
        selectinload(Document.versions).selectinload(DocumentVersion.tags).selectinload(DocumentVersionTag.tag)
    ).where(
        Document.id.in_(request.document_ids),
        Document.is_deleted == False
    )
    docs = (await db.execute(stmt)).scalars().all()

    if not docs:
        raise HTTPException(status_code=404, detail="No active documents found")

    export_files = []
    for doc in docs:
        if doc.is_restricted and current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
            continue

        v_stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id,
            DocumentVersion.version_num == doc.current_version
        )
        ver = (await db.execute(v_stmt)).scalar_one_or_none()
        if ver:
            file_path = await storage.get_file_path(ver.file_path)
            if os.path.exists(file_path):
                _, stored_ext = os.path.splitext(ver.file_path)
                safe_title = "".join([c for c in doc.title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
                download_filename = f"{safe_title}{stored_ext}" if stored_ext else safe_title
                export_files.append((file_path, download_filename))

    if not export_files:
        raise HTTPException(status_code=404, detail="No accessible files found to export")

    import zipfile
    import tempfile

    def iterfile():
        with tempfile.SpooledTemporaryFile(max_size=10*1024*1024, mode="w+b") as tmp:
            with zipfile.ZipFile(tmp, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path, arc_name in export_files:
                    zf.write(file_path, arc_name)
            tmp.seek(0)
            while True:
                chunk = tmp.read(65_536)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="documenti_selezionati.zip"',
        },
    )


# ── Preview in-browser ────────────────────────────────────────────────────────

@router.get("/{doc_id}/preview")
async def preview_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
):
    """Restituisce il file inline (Content-Disposition: inline) per anteprima browser."""
    doc = await _get_accessible_doc(doc_id, current_user, db)

    v_stmt = select(DocumentVersion).where(
        DocumentVersion.document_id == doc_id,
        DocumentVersion.version_num == doc.current_version,
    )
    ver = (await db.execute(v_stmt)).scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Versione non trovata.")

    file_path = await storage.get_file_path(ver.file_path)
    file_size = await asyncio.to_thread(os.path.getsize, file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    async def stream_file():
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(65_536)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        stream_file(),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.title}"',
            "Content-Length": str(file_size),
        },
    )


# ── Condivisione ──────────────────────────────────────────────────────────────

@router.post("/{doc_id}/share", response_model=DocumentShareResponse, status_code=201)
async def share_document(
    doc_id: UUID,
    payload: DocumentShareCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_accessible_doc(doc_id, current_user, db)
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo il proprietario può condividere.")

    target = (
        await db.execute(select(User).where(User.email == payload.shared_with_email))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Utente destinatario non trovato.")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Non puoi condividere con te stesso.")

    existing = (
        await db.execute(
            select(DocumentShare).where(
                DocumentShare.document_id == doc_id,
                DocumentShare.shared_with_id == target.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Documento già condiviso con questo utente.")

    share = DocumentShare(
        document_id=doc_id,
        shared_with_id=target.id,
        shared_by_id=current_user.id,
    )
    db.add(share)
    db.add(AuditLog(user_id=current_user.id, action="SHARE", target_id=doc_id))
    await db.commit()
    await db.refresh(share)
    return share


@router.get("/{doc_id}/shares", response_model=List[DocumentShareResponse])
async def list_shares(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_accessible_doc(doc_id, current_user, db)
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    stmt = select(DocumentShare).where(DocumentShare.document_id == doc_id)
    return list((await db.execute(stmt)).scalars().all())


@router.delete("/{doc_id}/shares/{share_id}", status_code=204)
async def revoke_share(
    doc_id: UUID,
    share_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_accessible_doc(doc_id, current_user, db)
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    share = (
        await db.execute(
            select(DocumentShare).where(
                DocumentShare.id == share_id, DocumentShare.document_id == doc_id
            )
        )
    ).scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Condivisione non trovata.")

    await db.execute(sa_delete(DocumentShare).where(DocumentShare.id == share_id))
    await db.commit()


# ── Download (streaming) ──────────────────────────────────────────────────────

@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    version: Optional[int] = None,
    inline: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
):
    doc = await _get_accessible_doc(doc_id, current_user, db)

    v_stmt = select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
    v_stmt = v_stmt.where(
        DocumentVersion.version_num == (version if version else doc.current_version)
    )
    ver = (await db.execute(v_stmt)).scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Versione non trovata.")

    file_path = await storage.get_file_path(ver.file_path)
    file_size = await asyncio.to_thread(os.path.getsize, file_path)
    _, stored_ext = os.path.splitext(ver.file_path)
    download_filename = f"{doc.title}{stored_ext}" if stored_ext else doc.title
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    async def stream_file():
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(65_536)
                if not chunk:
                    break
                yield chunk

    disposition = "inline" if inline else "attachment"
    return StreamingResponse(
        stream_file(),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{download_filename}"',
            "Content-Length": str(file_size),
        },
    )


# ── Versioni ──────────────────────────────────────────────────────────────────

@router.get("/{doc_id}/versions", response_model=List[DocumentVersionResponse])
async def get_document_history(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_accessible_doc(doc_id, current_user, db)
    v_stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    )
    return (await db.execute(v_stmt)).scalars().all()


# ── Statistiche ─────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_documents_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        # Se non è admin, torna le statistiche solo dei suoi documenti o vuoto
        filters = [Document.is_deleted == False, Document.owner_id == current_user.id]
    else:
        filters = [Document.is_deleted == False]
        
    # Totale documenti attivi
    total_docs_stmt = select(func.count(distinct(Document.id))).where(*filters)
    total_docs = (await db.execute(total_docs_stmt)).scalar() or 0
    
    # Per semplicità, in questa prima iterazione carichiamo tutti i documenti rilevanti
    # ed estraiamo i tag in memoria (essendo un JSON)
    docs_stmt = select(Document).options(selectinload(Document.metadata_entries)).where(*filters)
    docs = (await db.execute(docs_stmt)).scalars().all()
    
    tags_count = {}
    users_count = {}
    
    for d in docs:
        users_count[str(d.owner_id)] = users_count.get(str(d.owner_id), 0) + 1
        
        if d.metadata_entries and d.metadata_entries[0].metadata_json:
            doc_tags = d.metadata_entries[0].metadata_json.get("tags", [])
            for t in doc_tags:
                tags_count[t] = tags_count.get(t, 0) + 1
                
    # Ordinamento tag: top 10
    top_tags = dict(sorted(tags_count.items(), key=lambda item: item[1], reverse=True)[:10])
    
    return {
        "total_documents": total_docs,
        "by_tags": top_tags,
        "by_users": users_count
    }

# ── Cestino / Soft Delete ─────────────────────────────────────────────────────

@router.get("/trash", response_model=PaginatedDocuments)
async def get_trash(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        # User only sees their own deleted items
        filters = [Document.is_deleted == True, Document.owner_id == current_user.id]
    else:
        filters = [Document.is_deleted == True]

    count_stmt = select(func.count(distinct(Document.id))).select_from(Document).where(*filters)
    total: int = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(Document).options(
        selectinload(Document.metadata_entries),
        selectinload(Document.owner),
        selectinload(Document.content),
        selectinload(Document.versions)
    ).where(*filters).order_by(Document.deleted_at.desc()).offset(offset).limit(limit)

    documents = list((await db.execute(stmt)).scalars().unique().all())

    return PaginatedDocuments(
        items=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        limit=limit,
        offset=offset,
    )

@router.delete("/{doc_id}")
async def soft_delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
):
    stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or already in trash")
        
    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    doc.is_deleted = True
    doc.deleted_at = func.now()
    
    audit = AuditLog(user_id=current_user.id, action="SOFT_DELETE", target_id=doc.id)
    db.add(audit)
    
    await db.commit()

# ── Tags ──────────────────────────────────────────────────────────────────────

@router.post("/{doc_id}/versions/{version_id}/tags/{tag_id}/approve")
async def approve_document_tag(
    doc_id: UUID,
    version_id: UUID,
    tag_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from ..models.document import Document, DocumentVersionTag
    
    # Check permissions
    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    tag_stmt = select(DocumentVersionTag).where(
        DocumentVersionTag.document_version_id == version_id,
        DocumentVersionTag.tag_id == tag_id
    )
    doc_tag = (await db.execute(tag_stmt)).scalar_one_or_none()
    
    if not doc_tag:
        raise HTTPException(status_code=404, detail="Tag not found on this version")
        
    # Approving means it's no longer considered "AI generated" (suggested)
    doc_tag.is_ai_generated = False
    
    from ..models.audit import AuditLog
    db.add(AuditLog(user_id=current_user.id, action="APPROVE_TAG", target_id=doc_id, document_version_id=version_id))
    
    await db.commit()
    return {"message": "Tag approved successfully"}

@router.delete("/{doc_id}/versions/{version_id}/tags/{tag_id}")
async def delete_document_tag(
    doc_id: UUID,
    version_id: UUID,
    tag_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from ..models.document import Document, DocumentVersionTag
    
    # Check permissions
    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    tag_stmt = select(DocumentVersionTag).where(
        DocumentVersionTag.document_version_id == version_id,
        DocumentVersionTag.tag_id == tag_id
    )
    doc_tag = (await db.execute(tag_stmt)).scalar_one_or_none()
    
    if not doc_tag:
        raise HTTPException(status_code=404, detail="Tag not found on this version")
        
    await db.delete(doc_tag)
    
    from ..models.audit import AuditLog
    db.add(AuditLog(user_id=current_user.id, action="REJECT_DELETE_TAG", target_id=doc_id, document_version_id=version_id))
    
    await db.commit()
    return {"message": "Tag removed successfully"}
    
    if redis:
        try:
            async for key in redis.scan_iter(f"docs:{current_user.id}:*"):
                await redis.delete(key)
        except Exception:
            pass
            
    return {"message": "Document moved to trash"}

@router.post("/{doc_id}/restore", response_model=DocumentResponse)
async def restore_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
):
    stmt = select(Document).options(
        selectinload(Document.metadata_entries),
        selectinload(Document.owner),
        selectinload(Document.content),
        selectinload(Document.versions)
    ).where(Document.id == doc_id, Document.is_deleted == True)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in trash")
        
    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    doc.is_deleted = False
    doc.deleted_at = None
    
    audit = AuditLog(user_id=current_user.id, action="RESTORE", target_id=doc.id)
    db.add(audit)
    
    await db.commit()
    await db.refresh(doc)
    
    if redis:
        try:
            async for key in redis.scan_iter(f"docs:{current_user.id}:*"):
                await redis.delete(key)
        except Exception:
            pass
            
    return doc

@router.delete("/{doc_id}/hard")
async def hard_delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
    redis=Depends(get_redis)
):
    stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == doc_id, Document.is_deleted == True)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in trash. Soft delete it first.")
        
    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    # Delete associated files from storage
    if hasattr(doc, 'versions') and doc.versions:
        for ver in doc.versions:
            try:
                await storage.delete_file(ver.file_path)
            except Exception as e:
                logger.error(f"Failed to delete artifact {ver.file_path} for doc {doc_id}: {e}")
                
    # Delete from DB
    await db.delete(doc)
    
    audit = AuditLog(user_id=current_user.id, action="HARD_DELETE", target_id=doc.id)
    db.add(audit)
    
    await db.commit()
    
    return {"message": "Document permanently deleted"}

@router.post("/bulk-delete")
async def bulk_delete_documents(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
):
    if not request.document_ids:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    # Selection documents not already deleted
    stmt = select(Document).where(
        Document.id.in_(request.document_ids),
        Document.is_deleted == False
    )
    docs = (await db.execute(stmt)).scalars().all()

    if not docs:
        raise HTTPException(status_code=404, detail="No documents found to delete")

    deleted_count = 0
    for doc in docs:
        # Permission check: owner or ADMIN
        if current_user.role == UserRole.ADMIN or doc.owner_id == current_user.id:
            doc.is_deleted = True
            doc.deleted_at = func.now()
            db.add(AuditLog(user_id=current_user.id, action="SOFT_DELETE_BULK", target_id=doc.id))
            deleted_count += 1

    if deleted_count == 0:
        raise HTTPException(status_code=403, detail="Permission denied for all selected documents")

    await db.commit()

    if redis:
        try:
            async for key in redis.scan_iter(f"docs:{current_user.id}:*"):
                await redis.delete(key)
        except Exception:
            pass

    return {"message": f"Successfully moved {deleted_count} documents to trash"}
