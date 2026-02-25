from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, func
import uuid
from ..db import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False) # e.g., "UPLOAD", "DOWNLOAD", "DELETE", "VIEW"
    target_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
