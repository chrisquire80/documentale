import json
import hashlib
import logging
import mimetypes
import os
import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sa_update, or_, and_, distinct, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from ..db import get_db, SessionLocal
from ..models.user import User, UserRole
from ..models.document import Document, DocumentVersion, DocumentMetadata, DocumentContent
from ..models.audit import AuditLog
from ..schemas.doc_schemas import DocumentResponse, DocumentCreate, DocumentVersionResponse, PaginatedDocuments
from ..api.auth import get_current_user
from ..core.storage import get_storage, StorageLayer, LocalStorage
from ..core.cache import get_redis
from ..core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300


# ── Background task: OCR e aggiornamento FTS ─────────────────────────────────

async def _run_ocr_background(
    doc_id: UUID,
    file_rel_path: str,
    content_type: str,
    initial_corpus: str,
) -> None:
    """
    Eseguito dopo la risposta HTTP: estrae il testo dal file via OCR
    e aggiorna DocumentContent.fulltext_content.
    Il trigger PostgreSQL aggiornerà search_vector automaticamente.
    """
    from ..services.ocr import extract_text

    storage = LocalStorage()
    abs_path = await storage.get_file_path(file_rel_path)

    ocr_text = await extract_text(abs_path, content_type)
    if not ocr_text:
        return

    merged = f"{initial_corpus} {ocr_text}".strip()

    async with SessionLocal() as db:
        try:
            stmt = (
                sa_update(DocumentContent)
                .where(DocumentContent.document_id == doc_id)
                .values(fulltext_content=merged)
            )
            await db.execute(stmt)
            await db.commit()
            logger.info("OCR completata per documento %s (%d chars).", doc_id, len(merged))
        except Exception as exc:
            await db.rollback()
            logger.warning("Aggiornamento FTS fallito per %s: %s", doc_id, exc)


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
        raise HTTPException(status_code=400, detail="File type not allowed")

    # 1. Salva file
    file_rel_path = await storage.save_file(file.file, file.filename)

    # 2. Documento
    doc = Document(
        title=title,
        owner_id=current_user.id,
        is_restricted=is_restricted,
    )
    db.add(doc)
    await db.flush()

    # 3. Versione
    version = DocumentVersion(
        document_id=doc.id,
        version_num=1,
        file_path=file_rel_path,
    )
    db.add(version)

    # 4. Metadati
    metadata_data = json.loads(metadata_json)
    meta = DocumentMetadata(
        document_id=doc.id,
        metadata_json=metadata_data,
    )
    db.add(meta)

    # 5. DocumentContent con corpus base (titolo + metadati).
    #    L'OCR arricchirà fulltext_content in background dopo la risposta.
    tags_text = " ".join(metadata_data.get("tags", []))
    author_text = metadata_data.get("author", "")
    dept_text = metadata_data.get("dept", "")
    initial_corpus = " ".join(filter(None, [title, author_text, dept_text, tags_text]))
    doc_content = DocumentContent(
        document_id=doc.id,
        fulltext_content=initial_corpus,
    )
    db.add(doc_content)

    # 6. Audit log
    audit = AuditLog(user_id=current_user.id, action="UPLOAD", target_id=doc.id)
    db.add(audit)

    await db.commit()

    # Schedula OCR in background (non blocca la risposta HTTP)
    background_tasks.add_task(
        _run_ocr_background,
        doc.id,
        file_rel_path,
        file.content_type,
        initial_corpus,
    )

    # Invalida cache ricerche dell'utente
    if redis:
        try:
            async for key in redis.scan_iter(f"docs:{current_user.id}:*"):
                await redis.delete(key)
        except Exception:
            pass

    await db.refresh(doc, ["metadata_entries", "owner"])
    return doc


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=PaginatedDocuments)
@limiter.limit("120/minute")
async def search_documents(
    request: Request,
    query: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache_key = (
        f"docs:{current_user.id}:"
        + hashlib.md5(f"{query or ''}:{tag or ''}:{limit}:{offset}".encode()).hexdigest()
    )
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    filters = []
    need_content_join = False
    need_meta_join = False

    if current_user.role != UserRole.ADMIN:
        filters.append(
            or_(Document.is_restricted == False, Document.owner_id == current_user.id)
        )

    if query:
        need_content_join = True
        fts_condition = and_(
            DocumentContent.search_vector.isnot(None),
            DocumentContent.search_vector.op("@@")(func.plainto_tsquery("italian", query)),
        )
        filters.append(or_(fts_condition, Document.title.ilike(f"%{query}%")))

    if tag:
        need_meta_join = True
        filters.append(DocumentMetadata.metadata_json["tags"].contains([tag]))

    count_stmt = select(func.count(distinct(Document.id))).select_from(Document)
    if need_content_join:
        count_stmt = count_stmt.outerjoin(Document.content)
    if need_meta_join:
        count_stmt = count_stmt.outerjoin(Document.metadata_entries)
    if filters:
        count_stmt = count_stmt.where(*filters)

    total: int = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(Document).options(
        selectinload(Document.metadata_entries),
        selectinload(Document.owner),
    )
    if need_content_join:
        stmt = stmt.outerjoin(Document.content)
    if need_meta_join:
        stmt = stmt.outerjoin(Document.metadata_entries)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.offset(offset).limit(limit)

    documents = list((await db.execute(stmt)).scalars().unique().all())

    response = PaginatedDocuments(
        items=[DocumentResponse.model_validate(d) for d in documents],
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


# ── Download (streaming) ──────────────────────────────────────────────────────

@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    version: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
):
    stmt = select(Document).options(selectinload(Document.owner)).where(Document.id == doc_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.is_restricted and current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    v_stmt = select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
    if version:
        v_stmt = v_stmt.where(DocumentVersion.version_num == version)
    else:
        v_stmt = v_stmt.where(DocumentVersion.version_num == doc.current_version)

    ver = (await db.execute(v_stmt)).scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    file_path = await storage.get_file_path(ver.file_path)
    file_size = os.path.getsize(file_path)

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

    return StreamingResponse(
        stream_file(),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"',
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
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.is_restricted and current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    v_stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    )
    return (await db.execute(v_stmt)).scalars().all()
