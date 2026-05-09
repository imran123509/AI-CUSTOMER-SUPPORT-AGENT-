from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.ticket import Ticket, TicketNote, TicketStatus
from app.repositories.base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    model = Ticket

    async def list_for_org(
        self,
        org_id: UUID,
        *,
        status: TicketStatus | None = None,
        assignee_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Ticket]:
        stmt = select(Ticket).where(Ticket.organization_id == org_id)
        if status:
            stmt = stmt.where(Ticket.status == status)
        if assignee_id:
            stmt = stmt.where(Ticket.assignee_id == assignee_id)
        stmt = stmt.order_by(Ticket.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_by_status(self, org_id: UUID) -> dict[str, int]:
        stmt = (
            select(Ticket.status, func.count(Ticket.id))
            .where(Ticket.organization_id == org_id)
            .group_by(Ticket.status)
        )
        res = await self.session.execute(stmt)
        return {row[0].value: int(row[1]) for row in res.all()}


class TicketNoteRepository(BaseRepository[TicketNote]):
    model = TicketNote

    async def list_for_ticket(self, ticket_id: UUID) -> list[TicketNote]:
        stmt = (
            select(TicketNote)
            .where(TicketNote.ticket_id == ticket_id)
            .order_by(TicketNote.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
