import json
import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, distinct, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document, DocumentVersion, DocumentMetadata, DocumentContent
from ..models.audit import AuditLog
from ..schemas.doc_schemas import DocumentResponse, DocumentCreate, DocumentVersionResponse, PaginatedDocuments
from ..api.auth import get_current_user
from ..core.storage import get_storage, StorageLayer
from ..core.cache import get_redis

router = APIRouter(prefix="/documents", tags=["documents"])

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    title: str = Form(...),
    is_restricted: bool = Form(False),
    metadata_json: str = Form("{}"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
    redis=Depends(get_redis),
):
    # Validate file type
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

    # 1. Save file to storage
    file_rel_path = await storage.save_file(file.file, file.filename)

    # 2. Create Document entry
    doc = Document(
        title=title,
        owner_id=current_user.id,
        is_restricted=is_restricted,
    )
    db.add(doc)
    await db.flush()  # Get ID

    # 3. Create Version entry
    version = DocumentVersion(
        document_id=doc.id,
        version_num=1,
        file_path=file_rel_path,
    )
    db.add(version)

    # 4. Create Metadata entry
    metadata_data = json.loads(metadata_json)
    meta = DocumentMetadata(
        document_id=doc.id,
        metadata_json=metadata_data,
    )
    db.add(meta)

    # 5. Create DocumentContent for full-text search.
    # The DB trigger (installed at startup) will auto-populate search_vector
    # from fulltext_content, so we build a plain-text corpus here.
    tags_text = " ".join(metadata_data.get("tags", []))
    author_text = metadata_data.get("author", "")
    dept_text = metadata_data.get("dept", "")
    fulltext = " ".join(filter(None, [title, author_text, dept_text, tags_text]))
    doc_content = DocumentContent(
        document_id=doc.id,
        fulltext_content=fulltext,
    )
    db.add(doc_content)

    # 6. Audit log
    audit = AuditLog(user_id=current_user.id, action="UPLOAD", target_id=doc.id)
    db.add(audit)

    await db.commit()

    # Invalidate this user's search cache so new document appears immediately
    if redis:
        try:
            pattern = f"docs:{current_user.id}:*"
            async for key in redis.scan_iter(pattern):
                await redis.delete(key)
        except Exception:
            pass

    # Refresh the document with eager loading for relationships
    await db.refresh(doc, ["metadata_entries", "owner"])
    return doc


@router.get("/search", response_model=PaginatedDocuments)
async def search_documents(
    query: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    # --- Cache look-up ---
    cache_key = (
        f"docs:{current_user.id}:"
        + hashlib.md5(
            f"{query or ''}:{tag or ''}:{limit}:{offset}".encode()
        ).hexdigest()
    )
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # --- Build filter predicates ---
    filters = []
    need_content_join = False
    need_meta_join = False

    # RBAC: non-admin users see only their own restricted docs
    if current_user.role != UserRole.ADMIN:
        filters.append(
            or_(
                Document.is_restricted == False,
                Document.owner_id == current_user.id,
            )
        )

    if query:
        need_content_join = True
        # Use PostgreSQL FTS when a search_vector exists; fall back to ILIKE
        # for documents that pre-date the FTS feature.
        fts_condition = and_(
            DocumentContent.search_vector.isnot(None),
            DocumentContent.search_vector.op("@@")(
                func.plainto_tsquery("italian", query)
            ),
        )
        ilike_condition = Document.title.ilike(f"%{query}%")
        filters.append(or_(fts_condition, ilike_condition))

    if tag:
        need_meta_join = True
        filters.append(
            DocumentMetadata.metadata_json["tags"].contains([tag])
        )

    # --- COUNT query (for pagination metadata) ---
    count_stmt = select(func.count(distinct(Document.id))).select_from(Document)
    if need_content_join:
        count_stmt = count_stmt.outerjoin(Document.content)
    if need_meta_join:
        count_stmt = count_stmt.outerjoin(Document.metadata_entries)
    if filters:
        count_stmt = count_stmt.where(*filters)

    total_result = await db.execute(count_stmt)
    total: int = total_result.scalar() or 0

    # --- DATA query ---
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

    result = await db.execute(stmt)
    documents = list(result.scalars().unique().all())

    # --- Build response ---
    response = PaginatedDocuments(
        items=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        limit=limit,
        offset=offset,
    )

    # --- Populate cache ---
    if redis:
        try:
            await redis.setex(
                cache_key,
                _CACHE_TTL,
                json.dumps(response.model_dump(mode="json")),
            )
        except Exception:
            pass

    return response


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    version: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage),
):
    stmt = select(Document).options(
        selectinload(Document.owner)
    ).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # RBAC
    if (
        doc.is_restricted
        and current_user.role != UserRole.ADMIN
        and doc.owner_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Get version
    v_stmt = select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
    if version:
        v_stmt = v_stmt.where(DocumentVersion.version_num == version)
    else:
        v_stmt = v_stmt.where(DocumentVersion.version_num == doc.current_version)

    v_result = await db.execute(v_stmt)
    ver = v_result.scalar_one_or_none()

    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    file_path = await storage.get_file_path(ver.file_path)
    return FileResponse(path=file_path, filename=doc.title)


@router.get("/{doc_id}/versions", response_model=List[DocumentVersionResponse])
async def get_document_history(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if (
        doc.is_restricted
        and current_user.role != UserRole.ADMIN
        and doc.owner_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    v_stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    )
    v_result = await db.execute(v_stmt)
    return v_result.scalars().all()
