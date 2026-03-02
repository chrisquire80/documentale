import enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from ..db import Base


class LinkType(str, enum.Enum):
    segue_da = "segue_da"          # questo documento è follow-up di
    riferisce_a = "riferisce_a"    # si riferisce a / cita
    supera = "supera"              # sostituisce / aggiorna
    collegato_a = "collegato_a"   # genericamente correlato


class DocumentLink(Base):
    __tablename__ = "document_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_doc_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_doc_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type = Column(
        SAEnum(LinkType, name="link_type", create_type=True),
        nullable=False,
    )
    notes = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    from_doc = relationship("Document", foreign_keys=[from_doc_id])
    to_doc = relationship("Document", foreign_keys=[to_doc_id])
    creator = relationship("User", foreign_keys=[created_by])
