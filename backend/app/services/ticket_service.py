"""Ticket business logic — SLAs, AI summaries, escalation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.events import publish
from app.models.conversation import Conversation, ConversationStatus
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.repositories.ticket import TicketRepository
from app.services import ai_service

settings = get_settings()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_sla(priority: TicketPriority) -> tuple[datetime, datetime]:
    base_first = settings.sla_default_first_response_minutes
    base_resolution = settings.sla_default_resolution_hours
    multiplier = {
        TicketPriority.URGENT: 0.25,
        TicketPriority.HIGH: 0.5,
        TicketPriority.NORMAL: 1.0,
        TicketPriority.LOW: 2.0,
    }[priority]
    now = _utcnow()
    first_at = now + timedelta(minutes=base_first * multiplier)
    res_at = now + timedelta(hours=base_resolution * multiplier)
    return first_at, res_at


async def create_ticket(
    *,
    session: AsyncSession,
    organization_id: UUID,
    requester_id: UUID | None,
    subject: str,
    description: str | None,
    priority: TicketPriority = TicketPriority.NORMAL,
    category: str | None = None,
    conversation_id: UUID | None = None,
    tags: list[str] | None = None,
) -> Ticket:
    repo = TicketRepository(session)
    sla_first, sla_res = compute_sla(priority)
    ticket = await repo.create(
        organization_id=organization_id,
        requester_id=requester_id,
        subject=subject,
        description=description,
        priority=priority,
        category=category,
        conversation_id=conversation_id,
        sla_first_response_at=sla_first,
        sla_resolution_at=sla_res,
        tags=tags or [],
    )
    await publish(
        "unfyd:tickets",
        {
            "type": "ticket.created",
            "organization_id": str(organization_id),
            "ticket_id": str(ticket.id),
            "priority": priority.value,
        },
    )
    return ticket


async def auto_classify(session: AsyncSession, ticket: Ticket) -> None:
    """Run AI to fill in summary, category, priority for a fresh ticket."""
    text = f"Subject: {ticket.subject}\n\n{ticket.description or ''}"
    if not ticket.summary:
        try:
            ticket.summary = await ai_service.summarize_conversation(text)
        except Exception:
            ticket.summary = (ticket.description or ticket.subject)[:240]
    if not ticket.category:
        try:
            ticket.category = await ai_service.classify_category(text)
        except Exception:
            ticket.category = "general"
    if ticket.priority == TicketPriority.NORMAL:
        try:
            value = (await ai_service.classify_priority(text)).strip().lower()
            if value in {p.value for p in TicketPriority}:
                ticket.priority = TicketPriority(value)
                ticket.sla_first_response_at, ticket.sla_resolution_at = compute_sla(ticket.priority)
        except Exception:
            pass
    await session.flush()


async def escalate_to_human(
    session: AsyncSession,
    ticket: Ticket,
    *,
    target_agent_id: UUID | None = None,
    reason: str | None = None,
) -> Ticket:
    if target_agent_id:
        ticket.assignee_id = target_agent_id
    ticket.status = TicketStatus.OPEN
    if ticket.conversation_id:
        conv = await ConversationRepository(session).get(ticket.conversation_id)
        if conv:
            conv.status = ConversationStatus.HUMAN_HANDLING
            if target_agent_id:
                conv.assigned_agent_id = target_agent_id
    await publish(
        "unfyd:events",
        {
            "type": "ticket.escalated",
            "organization_id": str(ticket.organization_id),
            "ticket_id": str(ticket.id),
            "agent_id": str(target_agent_id) if target_agent_id else None,
            "reason": reason,
        },
    )
    await session.flush()
    return ticket


async def ticket_from_conversation(
    session: AsyncSession,
    conversation: Conversation,
) -> Ticket:
    """Materialise a ticket from a conversation, summarising via AI."""
    msgs = await MessageRepository(session).list_for_conversation(conversation.id, limit=200)
    transcript = "\n".join(f"{m.role.value}: {m.content}" for m in msgs)
    summary = transcript[:240]
    try:
        summary = await ai_service.summarize_conversation(transcript[-6000:])
    except Exception:
        pass
    subject = conversation.title or summary[:120]
    return await create_ticket(
        session=session,
        organization_id=conversation.organization_id,
        requester_id=conversation.user_id,
        subject=subject,
        description=transcript[-4000:],
        conversation_id=conversation.id,
    )
