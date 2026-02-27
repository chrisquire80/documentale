from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
import uuid
from ..db import Base

class DocumentComment(Base):
    __tablename__ = "document_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    content = Column(String, nullable=False)
    
    parent_id = Column(UUID(as_uuid=True), ForeignKey("document_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    document = relationship("Document")
    user = relationship("User")
    replies = relationship("DocumentComment", backref="parent", remote_side=[id])
