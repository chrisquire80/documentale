from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any, Dict
from ..models.user import UserRole

# Auth
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# User
class UserBase(BaseModel):
    email: EmailStr
    role: UserRole
    department: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

# Document
class DocumentBase(BaseModel):
    title: str
    is_restricted: bool = False
    doc_metadata: Dict[str, Any] = Field(default={})

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    is_restricted: Optional[bool] = None
    doc_metadata: Optional[Dict[str, Any]] = None

class TagResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class DocumentVersionTagResponse(BaseModel):
    is_ai_generated: bool
    status: str
    page_number: Optional[int] = None
    confidence: Optional[float] = None
    ai_reasoning: Optional[str] = None
    tag: TagResponse

    model_config = ConfigDict(from_attributes=True)

class DocumentVersionResponse(BaseModel):
    id: UUID
    version_num: int
    created_at: datetime
    ai_status: str
    ai_summary: Optional[str] = None
    ai_entities: Optional[Dict[str, Any]] = None
    ai_reasoning: Optional[str] = None
    tags: List[DocumentVersionTagResponse] = []

    model_config = ConfigDict(from_attributes=True)

class DocumentConflictResponse(BaseModel):
    id: UUID
    document_id: UUID
    reference_doc_id: Optional[UUID] = None
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    severity: str
    explanation: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentResponse(DocumentBase):
    id: UUID
    file_type: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    status: str
    current_version: int = 1
    current_version_id: Optional[UUID] = None
    owner_id: UUID
    is_deleted: bool = False
    created_at: datetime
    deleted_at: Optional[datetime] = None
    confidence_score: float = 0.0
    validation_method: Optional[str] = None
    validated_at: Optional[datetime] = None
    highlight_snippet: Optional[str] = None
    is_indexed: bool = False  # True se l'embedding AI è già stato generato
    relevance_score: Optional[float] = None
    
    versions: List[DocumentVersionResponse] = []
    current_version_rel: Optional[DocumentVersionResponse] = Field(None, alias="current_version_rel")
    conflicts: List[DocumentConflictResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class BulkExportRequest(BaseModel):
    document_ids: List[UUID]

class BulkDeleteRequest(BaseModel):
    document_ids: List[UUID]

class PaginatedDocuments(BaseModel):
    items: List[DocumentResponse]
    total: int
    limit: int
    offset: int


# Document Sharing
class DocumentShareCreate(BaseModel):
    shared_with_email: str

class DocumentShareResponse(BaseModel):
    id: UUID
    document_id: UUID
    shared_with_id: UUID
    shared_by_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
