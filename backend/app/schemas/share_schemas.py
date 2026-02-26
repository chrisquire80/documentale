from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class ShareCreate(BaseModel):
    expires_at: Optional[datetime] = None
    passkey: Optional[str] = Field(None, min_length=4, description="Optional raw passkey")

class ShareResponse(BaseModel):
    token: str
    expires_at: Optional[datetime] = None
    requires_passkey: bool
    document_id: UUID

class ShareInfoResponse(BaseModel):
    filename: str
    requires_passkey: bool

class ShareAccessRequest(BaseModel):
    passkey: Optional[str] = None
