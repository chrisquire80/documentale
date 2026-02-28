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


class ExtractedEntity(BaseModel):
    cls: str = Field(..., alias="class", description="Classe entità (party, date, amount, …)")
    text: str
    attributes: dict = {}
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    class Config:
        populate_by_name = True


class ExtractEntitiesResponse(BaseModel):
    document_id: str
    entity_count: int
    doc_type: Optional[str] = None
    parties: List[dict] = []
    dates: List[dict] = []
    amounts: List[dict] = []
    references: List[str] = []
    extracted_entities: List[dict] = []


class PageIndexResponse(BaseModel):
    document_id: str
    total_pages: int
    section_count: int
    page_index: dict
