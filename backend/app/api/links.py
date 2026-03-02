"""
Gestione dei link tra documenti.

Endpoints:
  GET    /documents/{id}/links          — lista link in uscita + entrata
  POST   /documents/{id}/links          — crea nuovo link
  DELETE /documents/links/{link_id}     — elimina link
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document
from ..models.link import DocumentLink, LinkType
from ..api.auth import get_current_user

router = APIRouter(prefix="/documents", tags=["links"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LinkCreate(BaseModel):
    to_doc_id: UUID
    relation_type: LinkType
    notes: Optional[str] = None


class LinkResponse(BaseModel):
    id: UUID
    from_doc_id: UUID
    to_doc_id: UUID
    relation_type: LinkType
    notes: Optional[str]
    created_at: str
    from_doc_title: Optional[str] = None
    to_doc_title: Optional[str] = None

    class Config:
        from_attributes = True


# ── Helper ─────────────────────────────────────────────────────────────────────

async def _doc_title(doc_id: UUID, db: AsyncSession) -> Optional[str]:
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    return doc.title if doc else None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/{doc_id}/links", response_model=List[LinkResponse])
async def get_document_links(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ritorna tutti i link (uscenti e entranti) per un documento."""
    stmt = (
        select(DocumentLink)
        .where(
            or_(
                DocumentLink.from_doc_id == doc_id,
                DocumentLink.to_doc_id == doc_id,
            )
        )
        .order_by(DocumentLink.created_at.desc())
    )
    links = (await db.execute(stmt)).scalars().all()

    result = []
    for link in links:
        result.append(
            LinkResponse(
                id=link.id,
                from_doc_id=link.from_doc_id,
                to_doc_id=link.to_doc_id,
                relation_type=link.relation_type,
                notes=link.notes,
                created_at=link.created_at.isoformat(),
                from_doc_title=await _doc_title(link.from_doc_id, db),
                to_doc_title=await _doc_title(link.to_doc_id, db),
            )
        )
    return result


@router.post("/{doc_id}/links", response_model=LinkResponse, status_code=201)
async def create_document_link(
    doc_id: UUID,
    body: LinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea un link tra il documento sorgente e un documento di destinazione."""
    if doc_id == body.to_doc_id:
        raise HTTPException(status_code=400, detail="Non puoi collegare un documento a se stesso.")

    from_doc = (
        await db.execute(select(Document).where(Document.id == doc_id, Document.is_deleted == False))
    ).scalar_one_or_none()
    to_doc = (
        await db.execute(select(Document).where(Document.id == body.to_doc_id, Document.is_deleted == False))
    ).scalar_one_or_none()

    if not from_doc or not to_doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")

    if from_doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Non hai i permessi per collegare questo documento.")

    link = DocumentLink(
        from_doc_id=doc_id,
        to_doc_id=body.to_doc_id,
        relation_type=body.relation_type,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return LinkResponse(
        id=link.id,
        from_doc_id=link.from_doc_id,
        to_doc_id=link.to_doc_id,
        relation_type=link.relation_type,
        notes=link.notes,
        created_at=link.created_at.isoformat(),
        from_doc_title=from_doc.title,
        to_doc_title=to_doc.title,
    )


@router.delete("/links/{link_id}", status_code=204)
async def delete_document_link(
    link_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Elimina un link tra documenti."""
    link = (await db.execute(select(DocumentLink).where(DocumentLink.id == link_id))).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link non trovato.")
    if link.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Non hai i permessi.")

    await db.delete(link)
    await db.commit()
