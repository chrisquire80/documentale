from sqlalchemy import Column, String, Integer, UUID, ForeignKey, DateTime, Boolean, JSON, func, Table, Index, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector
import uuid
import enum
from ..db import Base

class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class AIStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False, index=True)
    file_type = Column(String, nullable=True, index=True)   # MIME type, es. "application/pdf"
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    department = Column(String, nullable=True, index=True)
    status = Column(
        SQLEnum(DocumentStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=DocumentStatus.DRAFT,
        index=True
    )
    
    current_version_id = Column(UUID(as_uuid=True), ForeignKey("doc_versions.id", use_alter=True), nullable=True, index=True)
    
    is_restricted = Column(Boolean, default=False, index=True)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    owner = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", foreign_keys="[DocumentVersion.document_id]")
    current_version = relationship("DocumentVersion", foreign_keys=[current_version_id], post_update=True)
    
    metadata_entries = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan")
    content = relationship("DocumentContent", uselist=False, back_populates="document", cascade="all, delete-orphan")
    shares = relationship("DocumentShare", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_owner_restricted', 'owner_id', 'is_restricted'),
        Index('idx_created_at_desc', 'created_at'),
        Index('idx_not_deleted', 'is_deleted'),
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
    
    ai_status = Column(
        SQLEnum(AIStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=AIStatus.PENDING,
        index=True
    )
    ai_summary = Column(Text, nullable=True)
    vector_index_ref = Column(String, nullable=True)

    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])
    tags = relationship("DocumentVersionTag", back_populates="version", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_document_version', 'document_id', 'version_num'),
    )


class DocumentMetadata(Base):
    __tablename__ = "doc_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    metadata_json = Column(JSONB, nullable=False)  # {tags: [], dept: "", author: "", ...}

    document = relationship("Document", back_populates="metadata_entries")

    __table_args__ = (
        Index('idx_metadata_json_gin', 'metadata_json', postgresql_using='gin'),
    )


class DocumentContent(Base):
    __tablename__ = "doc_content"

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), primary_key=True)
    fulltext_content = Column(String, nullable=True)
    search_vector = Column(TSVECTOR)
    embedding = Column(Vector(3072)) # gemini-embedding-001 returns 3072 dimensions

    document = relationship("Document", back_populates="content")

    __table_args__ = (
        Index('idx_search_vector_gin', 'search_vector', postgresql_using='gin'),
        Index('idx_embedding_hnsw', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )


class DocumentShare(Base):
    """Condivisione esplicita di un documento riservato con un altro utente."""
    __tablename__ = "document_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    shared_with_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    shared_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="shares")
    shared_with = relationship("User", foreign_keys=[shared_with_id])
    shared_by = relationship("User", foreign_keys=[shared_by_id])

    __table_args__ = (
        Index('idx_share_doc_user', 'document_id', 'shared_with_id', unique=True),
    )

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)

class DocumentVersionTag(Base):
    __tablename__ = "doc_version_tags"
    
    document_version_id = Column(UUID(as_uuid=True), ForeignKey("doc_versions.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)
    is_ai_generated = Column(Boolean, default=False)
    
    version = relationship("DocumentVersion", back_populates="tags")
    tag = relationship("Tag")

