"""Ticket REST endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentMembership,
    CurrentUser,
    DBSession,
    require_agent,
)
from app.core.audit import audit_log
from app.core.exceptions import NotFoundError
from app.models.ticket import TicketPriority, TicketStatus
from app.repositories.ticket import TicketNoteRepository, TicketRepository
from app.schemas.ticket import (
    TicketCreate,
    TicketNoteCreate,
    TicketNoteOut,
    TicketOut,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter()


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    membership: CurrentMembership,
    session: DBSession,
    status_: TicketStatus | None = None,
    assignee_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
):
    rows = await TicketRepository(session).list_for_org(
        membership.organization_id,
        status=status_,
        assignee_id=assignee_id,
        limit=limit,
        offset=offset,
    )
    return [TicketOut.model_validate(t) for t in rows]


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    membership: CurrentMembership,
    user: CurrentUser,
    session: DBSession,
):
    ticket = await ticket_service.create_ticket(
        session=session,
        organization_id=membership.organization_id,
        requester_id=UUID(payload.requester_id) if payload.requester_id else user.id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        category=payload.category,
        conversation_id=UUID(payload.conversation_id) if payload.conversation_id else None,
        tags=payload.tags,
    )
    await ticket_service.auto_classify(session, ticket)
    await audit_log(
        session,
        organization_id=membership.organization_id,
        actor_id=user.id,
        action="ticket.created",
        target_type="ticket",
        target_id=str(ticket.id),
    )
    await session.commit()
    return TicketOut.model_validate(ticket)


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: UUID,
    membership: CurrentMembership,
    session: DBSession,
):
    repo = TicketRepository(session)
    ticket = await repo.get(ticket_id)
    if not ticket or ticket.organization_id != membership.organization_id:
        raise NotFoundError("Ticket not found")
    return TicketOut.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    membership: CurrentMembership,
    user: CurrentUser,
    session: DBSession,
):
    repo = TicketRepository(session)
    ticket = await repo.get(ticket_id)
    if not ticket or ticket.organization_id != membership.organization_id:
        raise NotFoundError("Ticket not found")

    fields = payload.model_dump(exclude_unset=True)
    if "assignee_id" in fields and fields["assignee_id"]:
        fields["assignee_id"] = UUID(fields["assignee_id"])
    if "status" in fields and fields["status"] == TicketStatus.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = datetime.now(timezone.utc)
    await repo.update(ticket, **fields)
    await audit_log(
        session,
        organization_id=membership.organization_id,
        actor_id=user.id,
        action="ticket.updated",
        target_type="ticket",
        target_id=str(ticket.id),
        metadata={"fields": list(fields.keys())},
    )
    await session.commit()
    return TicketOut.model_validate(ticket)


@router.post("/{ticket_id}/notes", response_model=TicketNoteOut, status_code=201)
async def add_note(
    ticket_id: UUID,
    payload: TicketNoteCreate,
    membership: CurrentMembership,
    user: CurrentUser,
    session: DBSession,
):
    ticket = await TicketRepository(session).get(ticket_id)
    if not ticket or ticket.organization_id != membership.organization_id:
        raise NotFoundError("Ticket not found")
    repo = TicketNoteRepository(session)
    note = await repo.create(
        ticket_id=ticket_id,
        author_id=user.id,
        body=payload.body,
        is_internal=payload.is_internal,
    )
    await session.commit()
    return TicketNoteOut.model_validate(note)


@router.get("/{ticket_id}/notes", response_model=list[TicketNoteOut])
async def list_notes(
    ticket_id: UUID,
    membership: CurrentMembership,
    session: DBSession,
):
    ticket = await TicketRepository(session).get(ticket_id)
    if not ticket or ticket.organization_id != membership.organization_id:
        raise NotFoundError("Ticket not found")
    rows = await TicketNoteRepository(session).list_for_ticket(ticket_id)
    return [TicketNoteOut.model_validate(n) for n in rows]


@router.post("/{ticket_id}/escalate", response_model=TicketOut)
async def escalate(
    ticket_id: UUID,
    membership: CurrentMembership,
    user: CurrentUser,
    session: DBSession,
    target_agent_id: str | None = None,
    reason: str | None = None,
    _=Depends(require_agent),
):
    ticket = await TicketRepository(session).get(ticket_id)
    if not ticket or ticket.organization_id != membership.organization_id:
        raise NotFoundError("Ticket not found")
    await ticket_service.escalate_to_human(
        session,
        ticket,
        target_agent_id=UUID(target_agent_id) if target_agent_id else None,
        reason=reason,
    )
    await audit_log(
        session,
        organization_id=membership.organization_id,
        actor_id=user.id,
        action="ticket.escalated",
        target_type="ticket",
        target_id=str(ticket.id),
    )
    await session.commit()
    return TicketOut.model_validate(ticket)
