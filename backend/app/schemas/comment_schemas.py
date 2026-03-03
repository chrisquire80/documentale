from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="The text content of the comment")
    parent_id: Optional[UUID] = None

class CommentUser(BaseModel):
    id: UUID
    email: str

class CommentResponse(BaseModel):
    id: UUID
    document_id: UUID
    parent_id: Optional[UUID] = None
    content: str
    created_at: datetime
    user: CommentUser

    class Config:
        from_attributes = True
