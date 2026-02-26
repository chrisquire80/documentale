from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any, Dict
from ..models.user import UserRole

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str

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

class DocumentVersionResponse(BaseModel):
    version_num: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentResponse(DocumentBase):
    id: UUID
    current_version: int
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedDocuments(BaseModel):
    items: List[DocumentResponse]
    total: int
    limit: int
    offset: int
