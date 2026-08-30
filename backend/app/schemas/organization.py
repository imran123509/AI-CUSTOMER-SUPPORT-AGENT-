from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.organization import MembershipRole
from app.schemas._types import UUIDStr


class OrganizationOut(BaseModel):
    id: UUIDStr
    name: str
    slug: str
    plan: str

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    id: UUIDStr
    organization_id: UUIDStr
    user_id: UUIDStr
    role: MembershipRole

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str
    role: MembershipRole = MembershipRole.MEMBER
    full_name: str | None = None


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    plan: str | None = None
    settings: dict | None = None
