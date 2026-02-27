from sqlalchemy import Column, String, Integer, UUID, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship
import uuid
import datetime
from ..db import Base

class DocumentShare(Base):
    __tablename__ = "document_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    token = Column(String, unique=True, nullable=False, index=True) # The public URL token
    hashed_passkey = Column(String, nullable=True) # Optional external passkey
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document")
    shared_by = relationship("User")

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        # Comparing with UTC now, assume expires_at is timezone-aware
        return self.expires_at < datetime.datetime.now(datetime.timezone.utc)
