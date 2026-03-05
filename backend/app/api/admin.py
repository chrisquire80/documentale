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
from ..models.segnalazione import GovernanceSegnalazione, GovernanceSegnalazioneHistory, AzioneSegnalazione
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


# ── Wave 7: Enterprise Governance Dashboard ────────────────────────────────

from ..models.document import DocumentVersion, AIStatus
from sqlalchemy.orm import selectinload
from sqlalchemy import desc

@router.get("/stats/dashboard")
async def get_dashboard_kpis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restituisce i KPI principali (Total Docs, AI Ready, Errors)."""
    _require_admin(current_user)

    total_stmt = select(func.count(Document.id)).where(Document.is_deleted == False)
    total_docs = (await db.execute(total_stmt)).scalar() or 0

    ready_stmt = (
        select(func.count(Document.id))
        .join(DocumentVersion, Document.current_version_id == DocumentVersion.id)
        .where(Document.is_deleted == False, DocumentVersion.ai_status == AIStatus.READY)
    )
    ai_ready_count = (await db.execute(ready_stmt)).scalar() or 0

    error_stmt = (
        select(func.count(Document.id))
        .join(DocumentVersion, Document.current_version_id == DocumentVersion.id)
        .where(Document.is_deleted == False, DocumentVersion.ai_status == AIStatus.ERROR)
    )
    indexing_errors = (await db.execute(error_stmt)).scalar() or 0

    ai_ready_percentage = round((ai_ready_count / total_docs * 100)) if total_docs > 0 else 0

    return {
        "total_documents": total_docs,
        "ai_ready_percentage": ai_ready_percentage,
        "indexing_errors": indexing_errors
    }

@router.get("/stats/departments")
async def get_departments_distribution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Distribuzione dei documenti per dipartimento."""
    _require_admin(current_user)

    stmt = (
        select(Document.department, func.count(Document.id).label("count"))
        .where(Document.is_deleted == False)
        .group_by(Document.department)
        .order_by(desc("count"))
    )
    rows = (await db.execute(stmt)).all()
    
    return [
        {"department": r.department or "Non Assegnato", "count": r.count}
        for r in rows
    ]

@router.get("/stats/queries")
async def get_top_queries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """I documenti più interrogati dall'AI negli ultimi 30 giorni."""
    _require_admin(current_user)

    stmt = (
        select(Document.title, func.count(AuditLog.id).label("query_count"))
        .join(Document, AuditLog.target_id == Document.id)
        .where(
            AuditLog.action == "AI_CHAT",
            AuditLog.timestamp >= func.now() - func.cast("30 days", type_=None)
        )
        .group_by(Document.title)
        .order_by(desc("query_count"))
        .limit(5)
    )
    rows = (await db.execute(stmt)).all()
    
    return [
        {"document_title": r.title, "query_count": r.query_count}
        for r in rows
    ]

@router.get("/audit-logs")
async def get_admin_audit_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log di Audit per la compliance AI Act."""
    _require_admin(current_user)

    stmt = (
        select(AuditLog, User.email, Document.title, Document.department)
        .outerjoin(User, AuditLog.user_id == User.id)
        .outerjoin(Document, AuditLog.target_id == Document.id)
        .where(AuditLog.action == "AI_CHAT")
        .order_by(desc(AuditLog.timestamp))
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    total_stmt = select(func.count(AuditLog.id)).where(AuditLog.action == "AI_CHAT")
    total = (await db.execute(total_stmt)).scalar() or 0

    logs_out = []
    for r in rows:
        audit, email, doc_title, doc_dept = r
        logs_out.append({
            "id": str(audit.id),
            "timestamp": audit.timestamp,
            "user_email": email or "System",
            "department": doc_dept or "Generale",
            "document_title": doc_title or "Multi-Document",
            "query": audit.query,
            "ai_response": audit.ai_response,
            "status": "Validata" # In futuro "Segnalata" integrando il feedback
        })

    return {
        "items": logs_out,
        "total": total,
        "page": skip // limit + 1,
        "size": limit
    }

# ── Wave 8: Governance Segnalazioni AI ────────────────────────────────────────

from ..models.segnalazione import (
    GovernanceSegnalazione,
    StatoSegnalazione,
    PrioritaSegnalazione,
)
import random
from datetime import datetime, timedelta, timezone


class SegnalazioneCreate(BaseModel):
    document_title: str
    document_id: UUID | None = None
    stato: StatoSegnalazione = StatoSegnalazione.segnalata
    priorita: PrioritaSegnalazione = PrioritaSegnalazione.media
    note: str | None = None


class SegnalazioneUpdate(BaseModel):
    stato: StatoSegnalazione | None = None
    note: str | None = None
    assigned_to: UUID | None = None


def _generate_report_code() -> str:
    """Genera un codice univoco tipo RPT-XXXXXX."""
    return f"RPT-{random.randint(100000, 999999)}"


@router.get("/governance/segnalazioni")
async def list_segnalazioni(
    stato: StatoSegnalazione | None = None,
    priorita: PrioritaSegnalazione | None = None,
    days: int = 30,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista delle segnalazioni Governance AI — solo per amministratori."""
    _require_admin(current_user)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(GovernanceSegnalazione).where(
        GovernanceSegnalazione.reported_at >= cutoff
    )

    if stato:
        stmt = stmt.where(GovernanceSegnalazione.stato == stato)
    if priorita:
        stmt = stmt.where(GovernanceSegnalazione.priorita == priorita)

    stmt = stmt.order_by(GovernanceSegnalazione.reported_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    count_stmt = select(func.count(GovernanceSegnalazione.id)).where(
        GovernanceSegnalazione.reported_at >= cutoff
    )
    if stato:
        count_stmt = count_stmt.where(GovernanceSegnalazione.stato == stato)
    if priorita:
        count_stmt = count_stmt.where(GovernanceSegnalazione.priorita == priorita)
    total: int = (await db.execute(count_stmt)).scalar() or 0

    return {
        "items": [
            {
                "id": str(s.id),
                "report_code": s.report_code,
                "document_title": s.document_title,
                "document_id": str(s.document_id) if s.document_id else None,
                "reported_at": s.reported_at,
                "stato": s.stato,
                "priorita": s.priorita,
                "note": s.note,
            }
            for s in rows
        ],
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
    }


@router.post("/governance/segnalazioni", status_code=201)
async def create_segnalazione(
    payload: SegnalazioneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea una nuova segnalazione Governance AI — solo per amministratori."""
    _require_admin(current_user)

    # Ensure uniqueness of report code with minimal retry
    for _ in range(5):
        code = _generate_report_code()
        existing = (
            await db.execute(
                select(GovernanceSegnalazione).where(
                    GovernanceSegnalazione.report_code == code
                )
            )
        ).scalar_one_or_none()
        if not existing:
            break

    segnalazione = GovernanceSegnalazione(
        report_code=code,
        document_title=payload.document_title,
        document_id=payload.document_id,
        stato=payload.stato,
        priorita=payload.priorita,
        note=payload.note,
        created_by=current_user.id,
    )
    db.add(segnalazione)
    await db.flush() # Get ID

    # Crea log in history
    from ..models.segnalazione import GovernanceSegnalazioneHistory, AzioneSegnalazione
    history_entry = GovernanceSegnalazioneHistory(
        segnalazione_id=segnalazione.id,
        action_type=AzioneSegnalazione.created,
        created_by_id=current_user.id
    )
    db.add(history_entry)
    await db.commit()

    return {
        "message": "Segnalazione creata con successo",
        "id": str(segnalazione.id),
        "report_code": segnalazione.report_code,
    }


@router.patch("/governance/segnalazioni/{segnalazione_id}")
async def update_segnalazione(
    segnalazione_id: UUID,
    payload: SegnalazioneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggiorna stato e/o note di una segnalazione — solo per amministratori."""
    _require_admin(current_user)

    stmt = select(GovernanceSegnalazione).where(
        GovernanceSegnalazione.id == segnalazione_id
    )
    segnalazione = (await db.execute(stmt)).scalar_one_or_none()
    if not segnalazione:
        raise HTTPException(status_code=404, detail="Segnalazione non trovata")

    from ..models.segnalazione import GovernanceSegnalazioneHistory, AzioneSegnalazione

    # Traccia modifiche per history
    if payload.stato is not None and payload.stato != segnalazione.stato:
        old_stato = segnalazione.stato.value
        new_stato = payload.stato.value
        segnalazione.stato = payload.stato
        
        history_entry = GovernanceSegnalazioneHistory(
            segnalazione_id=segnalazione.id,
            action_type=AzioneSegnalazione.status_changed,
            old_value=old_stato,
            new_value=new_stato,
            created_by_id=current_user.id
        )
        db.add(history_entry)

    if payload.note is not None and payload.note.strip():
        # Aggiungere nota è trattato come evento a sé stante
        segnalazione.note = payload.note
        
        history_entry = GovernanceSegnalazioneHistory(
            segnalazione_id=segnalazione.id,
            action_type=AzioneSegnalazione.note_added,
            new_value=payload.note,
            created_by_id=current_user.id
        )
        db.add(history_entry)

    if payload.assigned_to is not None:
        segnalazione.assigned_to = payload.assigned_to
        # Per semplicità, logghiamo l'assegnazione come azione
        history_entry = GovernanceSegnalazioneHistory(
            segnalazione_id=segnalazione.id,
            action_type=AzioneSegnalazione.assigned,
            new_value=str(payload.assigned_to),
            created_by_id=current_user.id
        )
        db.add(history_entry)

    await db.commit()
    return {"message": "Segnalazione aggiornata con successo"}

@router.get("/governance/segnalazioni/{segnalazione_id}")
async def get_segnalazione_audit_trail(
    segnalazione_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ottieni il dettaglio di una singola segnalazione con tutta la sua history."""
    _require_admin(current_user)
    
    from sqlalchemy.orm import selectinload
    stmt = (
        select(GovernanceSegnalazione)
        .options(
            selectinload(GovernanceSegnalazione.history).selectinload(GovernanceSegnalazioneHistory.created_by),
            selectinload(GovernanceSegnalazione.assigned_user)
        )
        .where(GovernanceSegnalazione.id == segnalazione_id)
    )
    segnalazione = (await db.execute(stmt)).scalar_one_or_none()
    
    if not segnalazione:
        raise HTTPException(status_code=404, detail="Segnalazione non trovata")
        
    history_res = []
    for h in segnalazione.history:
        username = h.created_by.email if h.created_by else "Sconosciuto"
        
        history_res.append({
            "id": h.id,
            "action_type": h.action_type.value,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "created_at": h.created_at,
            "created_by": username
        })
        
    from ..models.user import User as DBUser
    # Resolve main creator email
    u_main_stmt = select(DBUser).where(DBUser.id == segnalazione.created_by)
    u_main = (await db.execute(u_main_stmt)).scalar_one_or_none()

    assigned_email = segnalazione.assigned_user.email if segnalazione.assigned_user else "Non assegnato"
        
    return {
        "id": segnalazione.id,
        "report_code": segnalazione.report_code,
        "document_title": segnalazione.document_title,
        "document_id": segnalazione.document_id,
        "reported_at": segnalazione.reported_at,
        "stato": segnalazione.stato.value,
        "priorita": segnalazione.priorita.value,
        "note": segnalazione.note,
        "created_by": u_main.email if u_main else "Sconosciuto",
        "assigned_to": segnalazione.assigned_to,
        "assigned_to_email": assigned_email,
        "history": sorted(history_res, key=lambda x: x["created_at"])
    }

