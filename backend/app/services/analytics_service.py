"""Analytics queries.  Reads from PostgreSQL with optional Redis cache."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.ticket import Ticket, TicketStatus


async def dashboard_summary(session: AsyncSession, organization_id: UUID) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)

    active_conv_stmt = (
        select(func.count(Conversation.id))
        .where(Conversation.organization_id == organization_id)
        .where(Conversation.status.in_([ConversationStatus.OPEN, ConversationStatus.AI_HANDLING, ConversationStatus.HUMAN_HANDLING]))
    )
    open_tickets_stmt = (
        select(func.count(Ticket.id))
        .where(Ticket.organization_id == organization_id)
        .where(Ticket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.PENDING]))
    )
    resolved_today_stmt = (
        select(func.count(Ticket.id))
        .where(Ticket.organization_id == organization_id)
        .where(Ticket.resolved_at >= today_start)
    )
    avg_first_resp_stmt = select(
        func.avg(
            func.extract("epoch", Ticket.first_responded_at - Ticket.created_at)
        )
    ).where(Ticket.organization_id == organization_id, Ticket.first_responded_at.is_not(None))
    avg_resolution_stmt = select(
        func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at))
    ).where(Ticket.organization_id == organization_id, Ticket.resolved_at.is_not(None))
    csat_stmt = (
        select(func.avg(Ticket.csat_score))
        .where(Ticket.organization_id == organization_id)
        .where(Ticket.csat_score.is_not(None))
        .where(Ticket.resolved_at >= thirty_days_ago)
    )
    ai_latency_stmt = (
        select(func.avg(Message.latency_ms))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.organization_id == organization_id)
        .where(Message.role == MessageRole.ASSISTANT)
        .where(Message.created_at >= thirty_days_ago)
    )
    tokens_stmt = (
        select(func.coalesce(func.sum(Message.tokens), 0))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.organization_id == organization_id)
        .where(Message.created_at >= thirty_days_ago)
    )

    active_conversations = (await session.execute(active_conv_stmt)).scalar_one() or 0
    open_tickets = (await session.execute(open_tickets_stmt)).scalar_one() or 0
    resolved_today = (await session.execute(resolved_today_stmt)).scalar_one() or 0
    avg_first = (await session.execute(avg_first_resp_stmt)).scalar_one()
    avg_res = (await session.execute(avg_resolution_stmt)).scalar_one()
    csat = (await session.execute(csat_stmt)).scalar_one()
    ai_latency = (await session.execute(ai_latency_stmt)).scalar_one()
    tokens = (await session.execute(tokens_stmt)).scalar_one() or 0

    return {
        "active_conversations": int(active_conversations),
        "open_tickets": int(open_tickets),
        "resolved_today": int(resolved_today),
        "avg_first_response_seconds": float(avg_first) if avg_first is not None else None,
        "avg_resolution_seconds": float(avg_res) if avg_res is not None else None,
        "csat_30d": float(csat) if csat is not None else None,
        "ai_response_time_ms_avg": float(ai_latency) if ai_latency is not None else None,
        "tokens_used_30d": int(tokens),
    }


async def daily_message_volume(session: AsyncSession, organization_id: UUID, days: int = 14) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            func.date_trunc("day", Message.created_at).label("bucket"),
            func.count(Message.id).label("c"),
        )
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.organization_id == organization_id)
        .where(Message.created_at >= since)
        .group_by("bucket")
        .order_by("bucket")
    )
    res = await session.execute(stmt)
    return [{"bucket": row[0].isoformat(), "value": int(row[1])} for row in res.all()]


async def agent_productivity(session: AsyncSession, organization_id: UUID) -> list[dict]:
    """Resolved tickets per assignee in last 30 days."""
    since = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = (
        select(Ticket.assignee_id, func.count(Ticket.id))
        .where(Ticket.organization_id == organization_id)
        .where(Ticket.resolved_at >= since)
        .where(Ticket.assignee_id.is_not(None))
        .group_by(Ticket.assignee_id)
    )
    res = await session.execute(stmt)
    return [{"agent_id": str(row[0]), "resolved_count": int(row[1])} for row in res.all()]
