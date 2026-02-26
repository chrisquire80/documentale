from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, distinct
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import json

from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document, DocumentVersion, DocumentMetadata, DocumentContent
from ..models.audit import AuditLog
from ..schemas.doc_schemas import DocumentResponse, DocumentCreate, DocumentVersionResponse
from ..api.auth import get_current_user
from ..core.storage import get_storage, StorageLayer

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    title: str = Form(...),
    is_restricted: bool = Form(False),
    metadata_json: str = Form("{}"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage)
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
        "image/webp"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not allowed")

    # 1. Save file to storage
    file_rel_path = await storage.save_file(file.file, file.filename)
    
    # 2. Create Document entry
    doc = Document(
        title=title,
        owner_id=current_user.id,
        is_restricted=is_restricted
    )
    db.add(doc)
    await db.flush() # Get ID
    
    # 3. Create Version entry
    version = DocumentVersion(
        document_id=doc.id,
        version_num=1,
        file_path=file_rel_path
    )
    db.add(version)
    
    # 4. Create Metadata entry
    metadata_data = json.loads(metadata_json)
    meta = DocumentMetadata(
        document_id=doc.id,
        metadata_json=metadata_data
    )
    db.add(meta)
    
    # 5. Audit log
    audit = AuditLog(user_id=current_user.id, action="UPLOAD", target_id=doc.id)
    db.add(audit)
    
    await db.commit()

    # Refresh the document with eager loading for relationships
    await db.refresh(doc, ['metadata_entries', 'owner'])

    return doc

@router.get("/search", response_model=List[DocumentResponse])
async def search_documents(
    query: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Document).options(
        selectinload(Document.metadata_entries),
        selectinload(Document.owner)
    )

    # Only join metadata table if filtering by tag
    if tag:
        stmt = stmt.outerjoin(DocumentMetadata)

    filters = []

    # RBAC logic
    if current_user.role != UserRole.ADMIN:
        filters.append(or_(
            Document.is_restricted == False,
            Document.owner_id == current_user.id
        ))

    if query:
        # Simplified query for now, will implement full PG FTS later
        filters.append(Document.title.ilike(f"%{query}%"))

    if tag:
        filters.append(DocumentMetadata.metadata_json['tags'].contains([tag]))

    if filters:
        stmt = stmt.where(*filters)

    # Apply pagination
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().unique().all()

@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    version: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage)
):
    stmt = select(Document).options(
        selectinload(Document.owner)
    ).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # RBAC
    if doc.is_restricted and current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
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
    db: AsyncSession = Depends(get_db)
):
    # Basic permission check
    stmt = select(Document).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.is_restricted and current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    v_stmt = select(DocumentVersion).where(DocumentVersion.document_id == doc_id).order_by(DocumentVersion.version_num.desc())
    v_result = await db.execute(v_stmt)
    return v_result.scalars().all()
