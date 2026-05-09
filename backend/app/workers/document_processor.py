"""Background worker: parse + embed uploaded documents."""
from __future__ import annotations

from uuid import UUID

from app.core.database import session_scope
from app.core.events import ack, consume
from app.core.logging import get_logger
from app.models.knowledge_base import DocumentStatus
from app.repositories.knowledge_base import (
    DocumentChunkRepository,
    DocumentRepository,
)
from app.services import rag_service

logger = get_logger(__name__)
STREAM = "unfyd:docs"
GROUP = "doc-processors"
CONSUMER = "doc-1"


async def run() -> None:
    async for msg_id, event in consume(STREAM, GROUP, CONSUMER):
        try:
            if event.get("type") != "document.uploaded":
                await ack(STREAM, GROUP, msg_id)
                continue
            await _process(event)
        except Exception as exc:
            logger.exception("doc_processor.failed", error=str(exc), event=event)
        finally:
            await ack(STREAM, GROUP, msg_id)


async def _process(event: dict) -> None:
    document_id = UUID(event["document_id"])
    organization_id = UUID(event["organization_id"])
    storage_path = event["storage_path"]
    filename = event["filename"]
    mime_type = event.get("mime_type", "")

    async with session_scope() as session:
        doc_repo = DocumentRepository(session)
        chunk_repo = DocumentChunkRepository(session)
        doc = await doc_repo.get(document_id)
        if not doc:
            return
        doc.status = DocumentStatus.PROCESSING
        await session.flush()

    try:
        text = rag_service.parse_file(storage_path, mime_type, filename)
        if not text.strip():
            raise ValueError("Parsed document is empty")
        results = await rag_service.index_document(
            organization_id=organization_id,
            document_id=document_id,
            document_name=filename,
            text=text,
        )
    except Exception as exc:
        logger.exception("doc.index_failed", document_id=str(document_id), error=str(exc))
        async with session_scope() as session:
            doc = await DocumentRepository(session).get(document_id)
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error = str(exc)[:500]
        return

    async with session_scope() as session:
        doc = await DocumentRepository(session).get(document_id)
        chunk_repo = DocumentChunkRepository(session)
        if not doc:
            return
        for seq, (chroma_id, content, tokens) in enumerate(results):
            await chunk_repo.create(
                document_id=document_id,
                seq=seq,
                content=content,
                tokens=tokens,
                chroma_id=chroma_id,
            )
        doc.status = DocumentStatus.INDEXED
        doc.chunk_count = len(results)
        doc.error = None
    logger.info("doc.indexed", document_id=str(document_id), chunks=len(results))
