from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.knowledge_base import DocumentStatus


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None


class KnowledgeBaseOut(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: str
    knowledge_base_id: str
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
    knowledge_base_id: str | None = None


class SemanticSearchHit(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    score: float
    content: str


class SemanticSearchResponse(BaseModel):
    query: str
    hits: list[SemanticSearchHit]
