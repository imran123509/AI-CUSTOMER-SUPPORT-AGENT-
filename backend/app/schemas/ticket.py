from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.ticket import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TicketPriority = TicketPriority.NORMAL
    category: str | None = None
    requester_id: str | None = None
    conversation_id: str | None = None
    tags: list[str] = []


class TicketUpdate(BaseModel):
    subject: str | None = None
    description: str | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    category: str | None = None
    assignee_id: str | None = None
    tags: list[str] | None = None


class TicketOut(BaseModel):
    id: str
    organization_id: str
    conversation_id: str | None
    requester_id: str | None
    assignee_id: str | None
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
    id: str
    ticket_id: str
    author_id: str | None
    body: str
    is_internal: bool
    created_at: datetime

    model_config = {"from_attributes": True}
