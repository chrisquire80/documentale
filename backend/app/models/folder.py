from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import relationship, backref
import uuid
from ..db import Base


class Folder(Base):
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
    children = relationship(
        "Folder",
        cascade="all, delete-orphan",
        backref=backref("parent", remote_side=[id]),
    )
    documents = relationship("Document", back_populates="folder")

    __table_args__ = (
        Index('idx_folder_owner_parent', 'owner_id', 'parent_id'),
    )
