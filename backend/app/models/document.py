from sqlalchemy import Column, String, Integer, UUID, ForeignKey, DateTime, Boolean, JSON, func, Table, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
import uuid
from ..db import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False, index=True)
    current_version = Column(Integer, default=1)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    is_restricted = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    metadata_entries = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan")
    content = relationship("DocumentContent", uselist=False, back_populates="document", cascade="all, delete-orphan")

    # Composite index for common RBAC query pattern
    __table_args__ = (
        Index('idx_owner_restricted', 'owner_id', 'is_restricted'),
        Index('idx_created_at_desc', 'created_at'),
    )

    @property
    def doc_metadata(self):
        """Flatten metadata entries for easy access in schemas."""
        if self.metadata_entries:
            return self.metadata_entries[0].metadata_json
        return {}

class DocumentVersion(Base):
    __tablename__ = "doc_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    version_num = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    checksum = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="versions")

    # Composite index for efficient version lookups
    __table_args__ = (
        Index('idx_document_version', 'document_id', 'version_num'),
    )

class DocumentMetadata(Base):
    __tablename__ = "doc_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    metadata_json = Column(JSONB, nullable=False) # {tags: [], dept: "", author: "", ...}

    document = relationship("Document", back_populates="metadata_entries")

    # GIN index for efficient JSONB queries
    __table_args__ = (
        Index('idx_metadata_json_gin', 'metadata_json', postgresql_using='gin'),
    )

class DocumentContent(Base):
    __tablename__ = "doc_content"

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), primary_key=True)
    fulltext_content = Column(String, nullable=True)
    search_vector = Column(TSVECTOR)
    # embedding = Column(Vector(1536)) # Will require pgvector installation in migration

    document = relationship("Document", back_populates="content")
