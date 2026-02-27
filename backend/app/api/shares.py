import os
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document, DocumentVersion
from ..models.share import DocumentShare
from ..schemas.share_schemas import ShareCreate, ShareResponse, ShareInfoResponse, ShareAccessRequest
from ..api.auth import get_current_user
from ..core.security import get_password_hash, verify_password
from ..core.storage import get_storage, StorageLayer
import aiofiles
import mimetypes

router = APIRouter(tags=["shares"])

@router.post("/documents/{doc_id}/share", response_model=ShareResponse)
async def create_share(
    doc_id: UUID,
    req: ShareCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Document).where(Document.id == doc_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    token = secrets.token_urlsafe(32)
    hashed_passkey = get_password_hash(req.passkey) if req.passkey else None

    share = DocumentShare(
        document_id=doc_id,
        shared_by_id=current_user.id,
        token=token,
        hashed_passkey=hashed_passkey,
        expires_at=req.expires_at,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    return ShareResponse(
        token=share.token,
        expires_at=share.expires_at,
        requires_passkey=bool(share.hashed_passkey),
        document_id=doc_id
    )

@router.get("/shared/{token}", response_model=ShareInfoResponse)
async def get_shared_document_info(token: str, db: AsyncSession = Depends(get_db)):
    stmt = select(DocumentShare).options(selectinload(DocumentShare.document)).where(DocumentShare.token == token)
    share = (await db.execute(stmt)).scalar_one_or_none()
    
    if not share or share.is_expired():
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    doc = share.document
    return ShareInfoResponse(
        filename=doc.title,
        requires_passkey=bool(share.hashed_passkey)
    )

@router.post("/shared/{token}/download")
async def download_shared_document(
    token: str,
    req: ShareAccessRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageLayer = Depends(get_storage)
):
    stmt = select(DocumentShare).options(selectinload(DocumentShare.document)).where(DocumentShare.token == token)
    share = (await db.execute(stmt)).scalar_one_or_none()
    
    if not share or share.is_expired():
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    if share.hashed_passkey:
        if not req.passkey or not verify_password(req.passkey, share.hashed_passkey):
            raise HTTPException(status_code=401, detail="Invalid passkey")

    doc = share.document
    v_stmt = select(DocumentVersion).where(
        DocumentVersion.document_id == doc.id,
        DocumentVersion.version_num == doc.current_version
    )
    ver = (await db.execute(v_stmt)).scalar_one_or_none()
    
    if not ver:
        raise HTTPException(status_code=404, detail="File version not found")

    file_path = await storage.get_file_path(ver.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    file_size = os.path.getsize(file_path)
    _, stored_ext = os.path.splitext(ver.file_path)
    
    safe_title = "".join([c for c in doc.title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    download_filename = f"{safe_title}{stored_ext}" if stored_ext else safe_title
    
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
