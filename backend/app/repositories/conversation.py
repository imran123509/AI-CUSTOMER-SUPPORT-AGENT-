from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def list_for_org(
        self, org_id: UUID, *, status: ConversationStatus | None = None,
        limit: int = 50, offset: int = 0,
    ) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.organization_id == org_id)
        if status:
            stmt = stmt.where(Conversation.status == status)
        stmt = stmt.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def with_messages(self, conv_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(Conversation.id == conv_id)
            .options(selectinload(Conversation.messages))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def list_for_conversation(
        self, conv_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def add(
        self,
        *,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        sender_id: UUID | None = None,
        tokens: int | None = None,
        latency_ms: int | None = None,
        sentiment: str | None = None,
        metadata: dict | None = None,
    ) -> Message:
        return await self.create(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sender_id=sender_id,
            tokens=tokens,
            latency_ms=latency_ms,
            sentiment=sentiment,
            metadata_json=metadata or {},
        )
