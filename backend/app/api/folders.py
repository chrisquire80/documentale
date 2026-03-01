"""Folders API — crea, rinomina, cancella e sposta documenti in cartelle."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sa_update
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

from ..db import get_db
from ..models.folder import Folder
from ..models.document import Document
from ..api.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/folders", tags=["folders"])


# ── Schemi ────────────────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[UUID] = None


class FolderRename(BaseModel):
    name: str


class FolderResponse(BaseModel):
    id: UUID
    name: str
    parent_id: Optional[UUID] = None
    created_at: datetime
    children: list["FolderResponse"] = []

    model_config = {"from_attributes": True}


FolderResponse.model_rebuild()


class MoveDocumentRequest(BaseModel):
    folder_id: Optional[UUID] = None   # None = sposta nella root (nessuna cartella)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_folder_or_404(folder_id: UUID, user: User, db: AsyncSession) -> Folder:
    stmt = select(Folder).where(Folder.id == folder_id, Folder.owner_id == user.id)
    folder = (await db.execute(stmt)).scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Cartella non trovata.")
    return folder


def _build_tree(folders: list[Folder], parent_id=None) -> list[FolderResponse]:
    result = []
    for f in folders:
        if f.parent_id == parent_id:
            node = FolderResponse(
                id=f.id,
                name=f.name,
                parent_id=f.parent_id,
                created_at=f.created_at,
                children=_build_tree(folders, parent_id=f.id),
            )
            result.append(node)
    result.sort(key=lambda x: x.name.lower())
    return result


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[FolderResponse])
async def list_folders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restituisce l'albero completo delle cartelle dell'utente."""
    stmt = select(Folder).where(Folder.owner_id == current_user.id).order_by(Folder.name)
    folders = (await db.execute(stmt)).scalars().all()
    return _build_tree(list(folders))


@router.post("/", response_model=FolderResponse, status_code=201)
async def create_folder(
    body: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea una cartella (opzionalmente dentro una cartella padre)."""
    if body.parent_id:
        await _get_folder_or_404(body.parent_id, current_user, db)

    folder = Folder(name=body.name.strip(), parent_id=body.parent_id, owner_id=current_user.id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return FolderResponse(id=folder.id, name=folder.name, parent_id=folder.parent_id, created_at=folder.created_at)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def rename_folder(
    folder_id: UUID,
    body: FolderRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rinomina una cartella."""
    folder = await _get_folder_or_404(folder_id, current_user, db)
    folder.name = body.name.strip()
    await db.commit()
    await db.refresh(folder)
    return FolderResponse(id=folder.id, name=folder.name, parent_id=folder.parent_id, created_at=folder.created_at)


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancella la cartella. I documenti contenuti vengono spostati alla root
    (folder_id = NULL), non eliminati.
    """
    folder = await _get_folder_or_404(folder_id, current_user, db)

    # Sposta i documenti diretti alla root
    await db.execute(
        sa_update(Document)
        .where(Document.folder_id == folder_id)
        .values(folder_id=None)
    )

    await db.delete(folder)
    await db.commit()


@router.patch("/{folder_id}/documents/{doc_id}", status_code=204)
async def move_document(
    folder_id: UUID,
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sposta un documento in questa cartella."""
    await _get_folder_or_404(folder_id, current_user, db)

    stmt = select(Document).where(Document.id == doc_id, Document.owner_id == current_user.id, Document.is_deleted == False)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")

    doc.folder_id = folder_id
    await db.commit()


@router.delete("/{folder_id}/documents/{doc_id}", status_code=204)
async def remove_document_from_folder(
    folder_id: UUID,
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rimuove un documento dalla cartella (lo sposta alla root)."""
    stmt = select(Document).where(
        Document.id == doc_id,
        Document.owner_id == current_user.id,
        Document.folder_id == folder_id,
        Document.is_deleted == False,
    )
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato in questa cartella.")

    doc.folder_id = None
    await db.commit()
