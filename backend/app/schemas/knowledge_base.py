from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.knowledge_base import DocumentStatus
from app.schemas._types import UUIDStr


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None


class KnowledgeBaseOut(BaseModel):
    id: UUIDStr
    organization_id: UUIDStr
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: UUIDStr
    knowledge_base_id: UUIDStr
    filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    chunk_count: int
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int | None = None
    knowledge_base_id: UUIDStr | None = None


class SemanticSearchHit(BaseModel):
    chunk_id: UUIDStr
    document_id: UUIDStr
    document_name: str
    score: float
    content: str


class SemanticSearchResponse(BaseModel):
    query: str
    hits: list[SemanticSearchHit]
