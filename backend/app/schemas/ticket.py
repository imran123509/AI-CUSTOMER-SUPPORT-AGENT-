from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.ticket import TicketPriority, TicketStatus
from app.schemas._types import UUIDStr


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TicketPriority = TicketPriority.NORMAL
    category: str | None = None
    requester_id: UUIDStr | None = None
    conversation_id: UUIDStr | None = None
    tags: list[str] = []


class TicketUpdate(BaseModel):
    subject: str | None = None
    description: str | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    category: str | None = None
    assignee_id: UUIDStr | None = None
    tags: list[str] | None = None


class TicketOut(BaseModel):
    id: UUIDStr
    organization_id: UUIDStr
    conversation_id: UUIDStr | None
    requester_id: UUIDStr | None
    assignee_id: UUIDStr | None
    subject: str
    description: str | None
    summary: str | None
    category: str | None
    status: TicketStatus
    priority: TicketPriority
    sla_first_response_at: datetime | None
    sla_resolution_at: datetime | None
    first_responded_at: datetime | None
    resolved_at: datetime | None
    csat_score: int | None
    tags: list = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketNoteCreate(BaseModel):
    body: str
    is_internal: bool = True


class TicketNoteOut(BaseModel):
    id: UUIDStr
    ticket_id: UUIDStr
    author_id: UUIDStr | None
    body: str
    is_internal: bool
    created_at: datetime

    model_config = {"from_attributes": True}
