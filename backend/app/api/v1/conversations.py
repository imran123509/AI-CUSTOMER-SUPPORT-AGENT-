"""Conversation + message REST endpoints (HTTP — see ws/ for streaming)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    CurrentMembership,
    CurrentUser,
    DBSession,
    require_agent,
)
from app.core.exceptions import NotFoundError
from app.core.rate_limit import RateLimiter
from app.models.conversation import ConversationStatus
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.schemas.conversation import (
    ConversationDetail,
    ConversationOut,
    CreateConversationRequest,
    HandoffRequest,
    MessageOut,
    SendMessageRequest,
    SmartReplyRequest,
)
from app.services import ai_service, ticket_service

router = APIRouter()
ai_rate = RateLimiter(per_minute=60, key_prefix="rl:ai")


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    membership: CurrentMembership,
    session: DBSession,
    status_: ConversationStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    rows = await ConversationRepository(session).list_for_org(
        membership.organization_id, status=status_, limit=limit, offset=offset
    )
    return [ConversationOut.model_validate(c) for c in rows]


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: CreateConversationRequest,
    membership: CurrentMembership,
    user: CurrentUser,
    session: DBSession,
):
    repo = ConversationRepository(session)
    conv = await repo.create(
        organization_id=membership.organization_id,
        user_id=user.id,
        title=payload.title,
        status=ConversationStatus.AI_HANDLING,
    )
    if payload.initial_message:
        await ai_service.chat_complete(
            session=session,
            conversation=conv,
            user_message_text=payload.initial_message,
        )
    await session.commit()
    fresh = await repo.with_messages(conv.id)
    return ConversationDetail.model_validate(fresh)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    membership: CurrentMembership,
    session: DBSession,
):
    conv = await ConversationRepository(session).with_messages(conversation_id)
    if not conv or conv.organization_id != membership.organization_id:
        raise NotFoundError("Conversation not found")
    return ConversationDetail.model_validate(conv)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ai_rate)],
)
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    membership: CurrentMembership,
    user: CurrentUser,
    session: DBSession,
):
    conv = await ConversationRepository(session).get(conversation_id)
    if not conv or conv.organization_id != membership.organization_id:
        raise NotFoundError("Conversation not found")
    assistant_msg = await ai_service.chat_complete(
        session=session,
        conversation=conv,
        user_message_text=payload.content,
    )
    await session.commit()
    return MessageOut.model_validate(assistant_msg)


@router.post("/{conversation_id}/stream", dependencies=[Depends(ai_rate)])
async def stream_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    membership: CurrentMembership,
    session: DBSession,
):
    conv = await ConversationRepository(session).get(conversation_id)
    if not conv or conv.organization_id != membership.organization_id:
        raise NotFoundError("Conversation not found")

    async def gen():
        async for chunk in ai_service.chat_stream(
            session=session,
            conversation=conv,
            user_message_text=payload.content,
        ):
            yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: UUID,
    membership: CurrentMembership,
    session: DBSession,
    limit: int = 100,
    offset: int = 0,
):
    conv = await ConversationRepository(session).get(conversation_id)
    if not conv or conv.organization_id != membership.organization_id:
        raise NotFoundError("Conversation not found")
    msgs = await MessageRepository(session).list_for_conversation(
        conversation_id, limit=limit, offset=offset
    )
    return [MessageOut.model_validate(m) for m in msgs]


@router.post("/{conversation_id}/handoff", response_model=ConversationOut)
async def handoff(
    conversation_id: UUID,
    payload: HandoffRequest,
    membership: CurrentMembership,
    session: DBSession,
    _=Depends(require_agent),
):
    repo = ConversationRepository(session)
    conv = await repo.get(conversation_id)
    if not conv or conv.organization_id != membership.organization_id:
        raise NotFoundError("Conversation not found")
    conv.status = ConversationStatus.HUMAN_HANDLING
    if payload.target_agent_id:
        conv.assigned_agent_id = UUID(payload.target_agent_id)
    if not conv.ticket:
        await ticket_service.ticket_from_conversation(session, conv)
    await session.commit()
    return ConversationOut.model_validate(conv)


@router.post("/{conversation_id}/smart-replies")
async def smart_replies(
    conversation_id: UUID,
    payload: SmartReplyRequest,
    membership: CurrentMembership,
    session: DBSession,
    _=Depends(require_agent),
):
    conv = await ConversationRepository(session).get(conversation_id)
    if not conv or conv.organization_id != membership.organization_id:
        raise NotFoundError("Conversation not found")
    msgs = await MessageRepository(session).list_for_conversation(conversation_id, limit=200)
    transcript = "\n".join(f"{m.role.value}: {m.content}" for m in msgs[-payload.last_n :])
    suggestions = await ai_service.smart_replies(transcript)
    return {"suggestions": suggestions}
