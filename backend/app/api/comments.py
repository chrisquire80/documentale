from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document
from ..models.comment import DocumentComment
from ..schemas.comment_schemas import CommentCreate, CommentResponse
from ..api.auth import get_current_user
from ..api.ws import manager

router = APIRouter(prefix="/documents", tags=["comments"])

@router.get("/{doc_id}/comments", response_model=list[CommentResponse])
async def get_comments(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify access to the document
    d_stmt = select(Document).where(Document.id == doc_id)
    doc = (await db.execute(d_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.is_restricted and current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Fetch comments for the document ordered by creation desc for a flat feed
    stmt = select(DocumentComment).options(selectinload(DocumentComment.user)).where(DocumentComment.document_id == doc_id).order_by(DocumentComment.created_at.asc())
    comments = (await db.execute(stmt)).scalars().all()
    
    return [
        CommentResponse(
            id=c.id,
            document_id=c.document_id,
            content=c.content,
            created_at=c.created_at,
            user={"id": c.user.id, "email": c.user.email}
        ) for c in comments
    ]

@router.post("/{doc_id}/comments", response_model=CommentResponse)
async def create_comment(
    doc_id: UUID,
    req: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify access to the document
    d_stmt = select(Document).where(Document.id == doc_id)
    doc = (await db.execute(d_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.is_restricted and current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    comment = DocumentComment(
        document_id=doc_id,
        user_id=current_user.id,
        content=req.content.strip()
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    
    # Reload with user relationship
    stmt = select(DocumentComment).options(selectinload(DocumentComment.user)).where(DocumentComment.id == comment.id)
    loaded_comment = (await db.execute(stmt)).scalar_one()

    # Notify document owner if someone else commented
    if doc.owner_id != current_user.id:
        await manager.send_personal_message(
            {
                "type": "NEW_COMMENT",
                "message": f"{current_user.email} ha commentato sul tuo documento '{doc.title}'.",
                "doc_id": str(doc.id)
            },
            doc.owner_id
        )

    return CommentResponse(
        id=loaded_comment.id,
        document_id=loaded_comment.document_id,
        content=loaded_comment.content,
        created_at=loaded_comment.created_at,
        user={"id": loaded_comment.user.id, "email": loaded_comment.user.email}
    )
