from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="La domanda dell'utente")
    document_id: Optional[UUID] = Field(default=None, description="Se fornito, la ricerca RAG è confinata solo a questo documento")

class ChatSource(BaseModel):
    document_id: str
    title: str
    snippet: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource] = []
