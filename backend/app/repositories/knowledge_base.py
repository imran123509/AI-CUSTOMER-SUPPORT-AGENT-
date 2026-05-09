from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.knowledge_base import Document, DocumentChunk, KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    model = KnowledgeBase

    async def list_for_org(self, org_id: UUID) -> list[KnowledgeBase]:
        stmt = select(KnowledgeBase).where(KnowledgeBase.organization_id == org_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_default(self, org_id: UUID) -> KnowledgeBase | None:
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.organization_id == org_id)
            .order_by(KnowledgeBase.created_at.asc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class DocumentRepository(BaseRepository[Document]):
    model = Document

    async def list_for_kb(self, kb_id: UUID) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.knowledge_base_id == kb_id)
            .order_by(Document.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    model = DocumentChunk
