from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, func
import uuid
from ..db import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False) # e.g., "UPLOAD", "DOWNLOAD", "DELETE", "VIEW", "AI_CHAT"
    target_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Campi specifici per Audit AI (AI Act compliance)
    query = Column(String, nullable=True)
    document_version_id = Column(UUID(as_uuid=True), ForeignKey("doc_versions.id"), nullable=True, index=True)
    ai_response = Column(String, nullable=True)
