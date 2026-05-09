from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.models.conversation import ConversationStatus
from app.models.message import MessageRole


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_id: str | None
    role: MessageRole
    content: str
    tokens: int | None = None
    latency_ms: int | None = None
    sentiment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    organization_id: str
    user_id: str | None
    assigned_agent_id: str | None
    title: str | None
    status: ConversationStatus
    summary: str | None
    sentiment: str | None
    intent: str | None
    tags: list = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = []


class CreateConversationRequest(BaseModel):
    title: str | None = None
    initial_message: str | None = None


class SendMessageRequest(BaseModel):
    content: str
    role: MessageRole = MessageRole.USER
    stream: bool = False


class SmartReplyRequest(BaseModel):
    conversation_id: str
    last_n: int = 6


class HandoffRequest(BaseModel):
    target_agent_id: str | None = None
    reason: str | None = None
