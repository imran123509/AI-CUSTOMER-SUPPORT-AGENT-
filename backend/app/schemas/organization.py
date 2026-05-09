from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.organization import MembershipRole


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str
    plan: str

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    id: str
    organization_id: str
    user_id: str
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
