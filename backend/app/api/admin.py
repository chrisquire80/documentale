from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import csv
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from pydantic import BaseModel
from uuid import UUID

from ..api.auth import get_current_user
from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document
from ..models.audit import AuditLog
from ..core.cache import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: User):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Riservato agli amministratori.")


@router.get("/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """Statistiche Redis/cache — solo per amministratori."""
    _require_admin(current_user)

    if not redis:
        return {
            "redis_available": False,
            "message": "Redis non disponibile. La cache è disabilitata.",
        }

    try:
        info_stats = await redis.info("stats")
        info_memory = await redis.info("memory")

        hits: int = info_stats.get("keyspace_hits", 0)
        misses: int = info_stats.get("keyspace_misses", 0)
        total_ops = hits + misses
        hit_rate = round((hits / total_ops * 100), 1) if total_ops > 0 else 0.0

        cached_doc_keys = 0
        async for _ in redis.scan_iter("docs:*"):
            cached_doc_keys += 1

        return {
            "redis_available": True,
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate_percent": hit_rate,
            "total_operations": total_ops,
            "cached_doc_queries": cached_doc_keys,
            "used_memory_human": info_memory.get("used_memory_human", "N/A"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Errore Redis: {exc}")


@router.get("/document-stats")
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Statistiche documenti — solo per amministratori."""
    _require_admin(current_user)

    # Totale e attivi/cancellati
    total_stmt = select(func.count(Document.id))
    total: int = (await db.execute(total_stmt)).scalar() or 0

    deleted_stmt = select(func.count(Document.id)).where(Document.is_deleted == True)
    deleted: int = (await db.execute(deleted_stmt)).scalar() or 0

    # Documenti per tipo MIME
    by_type_stmt = (
        select(Document.file_type, func.count(Document.id).label("count"))
        .where(Document.is_deleted == False)
        .group_by(Document.file_type)
        .order_by(func.count(Document.id).desc())
    )
    by_type_rows = (await db.execute(by_type_stmt)).all()
    by_type = [{"file_type": r.file_type or "unknown", "count": r.count} for r in by_type_rows]

    # Caricamenti per giorno (ultimi 30 giorni)
    by_day_stmt = (
        select(
            func.date_trunc("day", Document.created_at).label("day"),
            func.count(Document.id).label("count"),
        )
        .where(
            Document.is_deleted == False,
            Document.created_at >= func.now() - func.cast("30 days", type_=None),
        )
        .group_by(func.date_trunc("day", Document.created_at))
        .order_by(func.date_trunc("day", Document.created_at))
    )
    by_day_rows = (await db.execute(by_day_stmt)).all()
    by_day = [{"day": str(r.day)[:10], "count": r.count} for r in by_day_rows]

    # Top 5 uploader (per numero di documenti)
    top_uploaders_stmt = (
        select(Document.owner_id, func.count(Document.id).label("count"))
        .where(Document.is_deleted == False)
        .group_by(Document.owner_id)
        .order_by(func.count(Document.id).desc())
        .limit(5)
    )
    top_uploaders_rows = (await db.execute(top_uploaders_stmt)).all()
    top_uploaders = [{"owner_id": str(r.owner_id), "count": r.count} for r in top_uploaders_rows]

    return {
        "total_documents": total,
        "active_documents": total - deleted,
        "deleted_documents": deleted,
        "by_file_type": by_type,
        "uploads_by_day": by_day,
        "top_uploaders": top_uploaders,
    }


# ── Modelli Pydantic per Admin ───────────────────────────────────────────────

class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None
    department: str | None = None

class UserAdminCreate(BaseModel):
    email: str
    password: str
    role: UserRole = UserRole.READER
    department: str | None = None


# ── Gestione Utenti ─────────────────────────────────────────────────────────

@router.get("/users")
async def get_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista utenti — solo per amministratori."""
    _require_admin(current_user)

    stmt = select(User).order_by(User.email).offset(skip).limit(limit)
    users = (await db.execute(stmt)).scalars().all()
    
    total_stmt = select(func.count(User.id))
    total: int = (await db.execute(total_stmt)).scalar() or 0

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "department": u.department,
                "is_active": u.is_active,
                "created_at": u.created_at
            }
            for u in users
        ],
        "total": total,
        "limit": limit,
        "offset": skip
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserAdminUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggiorna le proprieta' di un utente — solo per amministratori."""
    _require_admin(current_user)

    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role
    if payload.department is not None:
        user.department = payload.department

    await db.commit()
    return {"message": "Utente aggiornato con successo"}


@router.post("/users")
async def create_user_admin(
    payload: UserAdminCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea un utente in modo forzato — solo per amministratori."""
    _require_admin(current_user)

    stmt = select(User).where(User.email == payload.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email gia' in uso")

    hashed_password = pwd_context.hash(payload.password)
    new_user = User(
        email=payload.email,
        hashed_password=hashed_password,
        role=payload.role,
        department=payload.department,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {"message": "Utente creato", "user_id": new_user.id}


# ── Audit Log ───────────────────────────────────────────────────────────────

@router.get("/audit")
async def get_audit_logs(
    user_id: UUID | None = None,
    action: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Visualizza Audit Log — solo per amministratori."""
    _require_admin(current_user)

    stmt = select(AuditLog)
    
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    logs = (await db.execute(stmt)).scalars().all()
    
    count_stmt = select(func.count(AuditLog.id))
    if user_id: count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if action: count_stmt = count_stmt.where(AuditLog.action == action)
    total: int = (await db.execute(count_stmt)).scalar() or 0

    return {
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "target_id": log.target_id,
                "details": log.details,
                "timestamp": log.timestamp
            }
            for log in logs
        ],
        "limit": limit,
        "offset": skip
    }


@router.get("/audit/export")
async def export_audit_logs(
    user_id: UUID | None = None,
    action: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Esporta Audit Log in CSV — solo per amministratori."""
    _require_admin(current_user)

    stmt = select(AuditLog)
    
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        
    stmt = stmt.order_by(AuditLog.timestamp.desc())
    logs = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Intestazioni CSV
    writer.writerow(['ID', 'Data', 'Ora', 'Azione', 'Utente', 'Dettagli'])
    
    for log in logs:
        # Formattazione timestamp
        date_str = log.timestamp.strftime('%Y-%m-%d')
        time_str = log.timestamp.strftime('%H:%M:%S')
        user_str = str(log.user_id) if log.user_id else 'Sistema'
        
        writer.writerow([
            str(log.id),
            date_str,
            time_str,
            log.action,
            user_str,
            log.details or ''
        ])
        
    # Ripristina pointer all'inizio dello stream
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
    )

