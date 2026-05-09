"""Knowledge base + RAG REST endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import (
    CurrentMembership,
    CurrentUser,
    DBSession,
    require_admin,
)
from app.core.events import publish
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.models.knowledge_base import DocumentStatus
from app.repositories.knowledge_base import (
    DocumentRepository,
    KnowledgeBaseRepository,
)
from app.schemas.knowledge_base import (
    DocumentOut,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    SemanticSearchHit,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services import rag_service

router = APIRouter()


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_kbs(membership: CurrentMembership, session: DBSession):
    rows = await KnowledgeBaseRepository(session).list_for_org(membership.organization_id)
    return [KnowledgeBaseOut.model_validate(r) for r in rows]


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
async def create_kb(
    payload: KnowledgeBaseCreate,
    session: DBSession,
    membership=Depends(require_admin),
):
    repo = KnowledgeBaseRepository(session)
    kb = await repo.create(
        organization_id=membership.organization_id,
        name=payload.name,
        description=payload.description,
        chroma_collection=f"org_{str(membership.organization_id).replace('-', '')}",
    )
    await session.commit()
    return KnowledgeBaseOut.model_validate(kb)


@router.get("/{kb_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    kb_id: UUID,
    membership: CurrentMembership,
    session: DBSession,
):
    kb = await KnowledgeBaseRepository(session).get(kb_id)
    if not kb or kb.organization_id != membership.organization_id:
        raise NotFoundError("Knowledge base not found")
    docs = await DocumentRepository(session).list_for_kb(kb_id)
    return [DocumentOut.model_validate(d) for d in docs]


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    kb_id: UUID,
    session: DBSession,
    user: CurrentUser,
    membership=Depends(require_admin),
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
):
    kb = await KnowledgeBaseRepository(session).get(kb_id)
    if not kb or kb.organization_id != membership.organization_id:
        raise NotFoundError("Knowledge base not found")

    raw = await file.read()
    try:
        storage_path, sanitized = rag_service.safe_save_upload(
            raw_bytes=raw, original_name=file.filename or "upload"
        )
    except ValueError as exc:
        raise ValidationFailedError(str(exc)) from exc

    doc_repo = DocumentRepository(session)
    doc = await doc_repo.create(
        knowledge_base_id=kb_id,
        organization_id=membership.organization_id,
        uploaded_by=user.id,
        filename=sanitized,
        storage_path=storage_path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(raw),
        status=DocumentStatus.PENDING,
        metadata_json={"description": description} if description else {},
    )
    await session.commit()

    # Hand off to background worker via Redis Streams
    await publish(
        "unfyd:docs",
        {
            "type": "document.uploaded",
            "organization_id": str(membership.organization_id),
            "knowledge_base_id": str(kb_id),
            "document_id": str(doc.id),
            "storage_path": storage_path,
            "mime_type": doc.mime_type,
            "filename": sanitized,
        },
    )
    return DocumentOut.model_validate(doc)


@router.delete("/{kb_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: UUID,
    document_id: UUID,
    session: DBSession,
    membership=Depends(require_admin),
):
    kb = await KnowledgeBaseRepository(session).get(kb_id)
    if not kb or kb.organization_id != membership.organization_id:
        raise NotFoundError("Knowledge base not found")
    repo = DocumentRepository(session)
    doc = await repo.get(document_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise NotFoundError("Document not found")
    await rag_service.remove_document(membership.organization_id, document_id)
    await repo.delete(doc)
    await session.commit()


@router.post("/search", response_model=SemanticSearchResponse)
async def semantic_search(
    payload: SemanticSearchRequest,
    membership: CurrentMembership,
):
    hits = await rag_service.semantic_search(
        organization_id=membership.organization_id,
        query=payload.query,
        top_k=payload.top_k,
    )
    return SemanticSearchResponse(
        query=payload.query,
        hits=[SemanticSearchHit(**h) for h in hits],
    )
