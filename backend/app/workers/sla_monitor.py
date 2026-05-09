"""Worker: periodically scans tickets for SLA breaches and raises events."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import session_scope
from app.core.events import publish
from app.core.logging import get_logger
from app.models.ticket import Ticket, TicketStatus

logger = get_logger(__name__)
INTERVAL_SECONDS = 60


async def run() -> None:
    while True:
        try:
            await _tick()
        except Exception as exc:
            logger.exception("sla_monitor.tick_failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)


async def _tick() -> None:
    now = datetime.now(timezone.utc)
    async with session_scope() as session:
        stmt = (
            select(Ticket)
            .where(Ticket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.PENDING]))
            .where(
                (Ticket.sla_first_response_at.is_not(None) & (Ticket.sla_first_response_at < now) & Ticket.first_responded_at.is_(None))
                | (Ticket.sla_resolution_at.is_not(None) & (Ticket.sla_resolution_at < now) & Ticket.resolved_at.is_(None))
            )
        )
        rows = (await session.execute(stmt)).scalars().all()
    for t in rows:
        breach = []
        if t.sla_first_response_at and t.sla_first_response_at < now and not t.first_responded_at:
            breach.append("first_response")
        if t.sla_resolution_at and t.sla_resolution_at < now and not t.resolved_at:
            breach.append("resolution")
        if not breach:
            continue
        await publish(
            "unfyd:events",
            {
                "type": "ticket.sla_breach",
                "organization_id": str(t.organization_id),
                "ticket_id": str(t.id),
                "breach": breach,
            },
        )
        logger.warning("sla.breach", ticket_id=str(t.id), breach=breach)
