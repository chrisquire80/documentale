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
from sqlalchemy import select, update as sa_update, delete as sa_delete, or_, and_, distinct, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from ..db import get_db, SessionLocal
from ..models.user import User, UserRole
from ..models.document import Document, DocumentVersion, DocumentMetadata, DocumentContent, DocumentShare
from ..models.audit import AuditLog
from ..schemas.doc_schemas import (
    DocumentResponse, DocumentVersionResponse, PaginatedDocuments,
    DocumentUpdate, DocumentShareCreate, DocumentShareResponse,
)
from ..api.auth import get_current_user
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
) -> None:
    from ..services.ocr import extract_text
    from ..services.gemini_tagger import suggest_tags

    storage = LocalStorage()
    abs_path = await storage.get_file_path(file_rel_path)

    ocr_text = await extract_text(abs_path, content_type)
    merged = f"{initial_corpus} {ocr_text}".strip() if ocr_text else initial_corpus

    # Auto-tagging Gemini (graceful degradation — mai blocca)
    async with SessionLocal() as db:
        try:
            doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
            title = doc.title if doc else ""
        except Exception:
            title = ""

    tags = await suggest_tags(merged, title)

    async with SessionLocal() as db:
        try:
            await db.execute(
                sa_update(DocumentContent)
                .where(DocumentContent.document_id == doc_id)
                .values(fulltext_content=merged)
            )

            if tags:
                meta = (
                    await db.execute(
                        select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id)
                    )
                ).scalar_one_or_none()
                if meta:
                    existing = dict(meta.metadata_json or {})
                    existing["tags"] = list(dict.fromkeys(existing.get("tags", []) + tags))
                    existing["ai_tags"] = tags
                    await db.execute(
                        sa_update(DocumentMetadata)
                        .where(DocumentMetadata.document_id == doc_id)
                        .values(metadata_json=existing)
                    )

            await db.commit()
            logger.info("OCR+tag completati per documento %s (%d chars).", doc_id, len(merged))
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
    )
    db.add(doc)
    await db.flush()

    db.add(DocumentVersion(document_id=doc.id, version_num=1, file_path=file_rel_path))
    db.add(DocumentMetadata(document_id=doc.id, metadata_json=metadata_data))

    tags_text = " ".join(metadata_data.get("tags", []))
    author_text = metadata_data.get("author", "")
    dept_text = metadata_data.get("dept", "")
    initial_corpus = " ".join(filter(None, [title, author_text, dept_text, tags_text]))
    db.add(DocumentContent(document_id=doc.id, fulltext_content=initial_corpus))
    db.add(AuditLog(user_id=current_user.id, action="UPLOAD", target_id=doc.id))

    await db.commit()

    background_tasks.add_task(
        _run_ocr_background, doc.id, file_rel_path, file.content_type, initial_corpus
    )
    await _invalidate_user_cache(redis, current_user.id)

    await db.refresh(doc, ["metadata_entries", "owner"])
    return doc


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
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache_key = (
        f"docs:{current_user.id}:"
        + hashlib.md5(
            f"{query}:{tag}:{file_type}:{date_from}:{date_to}:{limit}:{offset}".encode()
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
        fts_cond = and_(
            DocumentContent.search_vector.isnot(None),
            DocumentContent.search_vector.op("@@")(func.plainto_tsquery("italian", query)),
        )
        filters.append(or_(fts_cond, Document.title.ilike(f"%{query}%")))

    if tag:
        need_meta_join = True
        filters.append(DocumentMetadata.metadata_json["tags"].contains([tag]))

    if file_type:
        filters.append(Document.file_type == file_type)

    if date_from:
        filters.append(Document.created_at >= date_from)

    if date_to:
        filters.append(Document.created_at <= date_to)

    count_stmt = select(func.count(distinct(Document.id))).select_from(Document)
    if need_content_join:
        count_stmt = count_stmt.outerjoin(Document.content)
    if need_meta_join:
        count_stmt = count_stmt.outerjoin(Document.metadata_entries)
    count_stmt = count_stmt.where(*filters)
    total: int = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Document)
        .options(selectinload(Document.metadata_entries), selectinload(Document.owner))
        .order_by(Document.created_at.desc())
    )
    if need_content_join:
        stmt = stmt.outerjoin(Document.content)
    if need_meta_join:
        stmt = stmt.outerjoin(Document.metadata_entries)
    stmt = stmt.where(*filters).offset(offset).limit(limit)

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


# ── Cestino ───────────────────────────────────────────────────────────────────

@router.get("/trash", response_model=PaginatedDocuments)
async def list_trash(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Documenti eliminati: solo i propri per utenti normali, tutti per ADMIN."""
    where = [Document.is_deleted == True]
    if current_user.role != UserRole.ADMIN:
        where.append(Document.owner_id == current_user.id)

    total: int = (await db.execute(select(func.count(Document.id)).where(*where))).scalar() or 0

    stmt = (
        select(Document)
        .options(selectinload(Document.metadata_entries), selectinload(Document.owner))
        .where(*where)
        .order_by(Document.deleted_at.desc())
        .offset(offset)
        .limit(limit)
    )
    docs = list((await db.execute(stmt)).scalars().unique().all())

    return PaginatedDocuments(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── Modifica metadati ─────────────────────────────────────────────────────────

@router.patch("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: UUID,
    payload: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    doc = await _get_accessible_doc(doc_id, current_user, db)
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo il proprietario o un admin possono modificare.")

    if payload.title is not None:
        doc.title = payload.title
    if payload.is_restricted is not None:
        doc.is_restricted = payload.is_restricted

    if payload.metadata_json is not None:
        meta = (
            await db.execute(select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id))
        ).scalar_one_or_none()
        if meta:
            meta.metadata_json = payload.metadata_json
        else:
            db.add(DocumentMetadata(document_id=doc_id, metadata_json=payload.metadata_json))

    db.add(AuditLog(user_id=current_user.id, action="EDIT", target_id=doc_id))
    await db.commit()
    await db.refresh(doc, ["metadata_entries", "owner"])
    await _invalidate_user_cache(redis, current_user.id)
    return doc


# ── Soft delete ───────────────────────────────────────────────────────────────

@router.delete("/{doc_id}", status_code=204)
async def soft_delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    doc.is_deleted = True
    doc.deleted_at = datetime.now(timezone.utc)
    db.add(AuditLog(user_id=current_user.id, action="DELETE", target_id=doc_id))
    await db.commit()
    await _invalidate_user_cache(redis, current_user.id)


# ── Ripristino dal cestino ────────────────────────────────────────────────────

@router.post("/{doc_id}/restore", response_model=DocumentResponse)
async def restore_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    stmt = (
        select(Document)
        .options(selectinload(Document.metadata_entries), selectinload(Document.owner))
        .where(Document.id == doc_id, Document.is_deleted == True)
    )
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato nel cestino.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    doc.is_deleted = False
    doc.deleted_at = None
    db.add(AuditLog(user_id=current_user.id, action="RESTORE", target_id=doc_id))
    await db.commit()
    await db.refresh(doc, ["metadata_entries", "owner"])
    await _invalidate_user_cache(redis, current_user.id)
    return doc


# ── Eliminazione permanente ───────────────────────────────────────────────────

@router.delete("/{doc_id}/permanent", status_code=204)
async def permanent_delete(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
    redis=Depends(get_redis),
):
    """Eliminazione definitiva con rimozione file fisici (proprietario o ADMIN)."""
    stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == doc_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    for ver in doc.versions:
        try:
            fp = await storage.get_file_path(ver.file_path)
            if os.path.exists(fp):
                os.remove(fp)
        except Exception as exc:
            logger.warning("Impossibile eliminare file %s: %s", ver.file_path, exc)

    await db.execute(sa_delete(Document).where(Document.id == doc_id))
    await db.commit()
    await _invalidate_user_cache(redis, current_user.id)


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
    file_size = os.path.getsize(file_path)
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
    doc = await _get_accessible_doc(doc_id, current_user, db)
    v_stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    )
    return (await db.execute(v_stmt)).scalars().all()
