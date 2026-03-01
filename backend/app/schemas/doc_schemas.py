from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any, Dict
from ..models.user import UserRole
from ..models.document import DocumentStatus

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

    class Config:
        from_attributes = True

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

class DocumentVersionResponse(BaseModel):
    version_num: int
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentResponse(DocumentBase):
    id: UUID
    file_type: Optional[str] = None
    current_version: int
    owner_id: UUID
    is_deleted: bool = False
    status: DocumentStatus = DocumentStatus.draft
    folder_id: Optional[UUID] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True
