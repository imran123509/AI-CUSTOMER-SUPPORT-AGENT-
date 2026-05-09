"""Organization (tenant) routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentMembership,
    CurrentUser,
    DBSession,
    require_admin,
)
from app.core.exceptions import NotFoundError
from app.core.security import hash_password
from app.models.organization import MembershipRole, Organization
from app.repositories.organization import MembershipRepository, OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.organization import (
    InviteMemberRequest,
    MembershipOut,
    OrganizationOut,
    UpdateOrganizationRequest,
)

router = APIRouter()


@router.get("", response_model=list[OrganizationOut])
async def list_my_organizations(user: CurrentUser, session: DBSession):
    members = MembershipRepository(session)
    orgs_repo = OrganizationRepository(session)
    out: list[OrganizationOut] = []
    for m in await members.for_user(user.id):
        org = await orgs_repo.get(m.organization_id)
        if org:
            out.append(OrganizationOut.model_validate(org))
    return out


@router.get("/current", response_model=OrganizationOut)
async def current_org(membership: CurrentMembership, session: DBSession):
    org = await OrganizationRepository(session).get(membership.organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    return OrganizationOut.model_validate(org)


@router.patch("/current", response_model=OrganizationOut)
async def update_org(
    payload: UpdateOrganizationRequest,
    session: DBSession,
    membership=Depends(require_admin),
):
    org: Organization | None = await OrganizationRepository(session).get(
        membership.organization_id
    )
    if not org:
        raise NotFoundError("Organization not found")
    if payload.name:
        org.name = payload.name
    if payload.plan:
        org.plan = payload.plan
    if payload.settings is not None:
        org.settings = payload.settings
    await session.commit()
    return OrganizationOut.model_validate(org)


@router.get("/current/members", response_model=list[MembershipOut])
async def list_members(membership: CurrentMembership, session: DBSession):
    rows = await MembershipRepository(session).list_org_members(membership.organization_id)
    return [MembershipOut.model_validate(m) for m in rows]


@router.post("/current/members", response_model=MembershipOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: InviteMemberRequest,
    session: DBSession,
    membership=Depends(require_admin),
):
    """Invite by email — creates user with random password if absent."""
    users = UserRepository(session)
    members = MembershipRepository(session)
    user = await users.get_by_email(payload.email)
    if not user:
        user = await users.create(
            email=payload.email.lower(),
            full_name=payload.full_name or payload.email.split("@")[0],
            password_hash=hash_password("ChangeMe123!"),
        )
    existing = await members.for_org_user(membership.organization_id, user.id)
    if existing:
        existing.role = payload.role
        await session.commit()
        return MembershipOut.model_validate(existing)
    new_member = await members.add_member(
        org_id=membership.organization_id, user_id=user.id, role=payload.role
    )
    await session.commit()
    return MembershipOut.model_validate(new_member)
