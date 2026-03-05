import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Enum, func, Integer
from sqlalchemy.orm import relationship

from ..db import Base


class StatoSegnalazione(str, PyEnum):
    segnalata = "segnalata"
    in_revisione = "in_revisione"
    risolta = "risolta"


class PrioritaSegnalazione(str, PyEnum):
    alta = "alta"
    media = "media"
    bassa = "bassa"


class GovernanceSegnalazione(Base):
    __tablename__ = "governance_segnalazioni"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Es: RPT-123456 — generato dal backend al momento della creazione
    report_code = Column(String, nullable=False, unique=True, index=True)
    # Documento associato (titolo testuale per display, FK opzionale)
    document_title = Column(String, nullable=False)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    stato = Column(
        Enum(StatoSegnalazione, name="stato_segnalazione_enum"),
        nullable=False,
        default=StatoSegnalazione.segnalata,
    )
    priorita = Column(
        Enum(PrioritaSegnalazione, name="priorita_segnalazione_enum"),
        nullable=False,
        default=PrioritaSegnalazione.media,
    )
    note = Column(String, nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
