"""Reusable FastAPI dependencies — auth, current user, current org, RBAC."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.organization import Membership, MembershipRole
from app.models.user import User
from app.repositories.organization import MembershipRepository, OrganizationRepository
from app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: DBSession,
) -> User:
    if not token:
        raise UnauthorizedError("Missing bearer token")
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject")
    user = await UserRepository(session).get(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_org(
    user: CurrentUser,
    session: DBSession,
    x_org_id: Annotated[str | None, Header(alias="X-Org-Id")] = None,
) -> Membership:
    """Returns the membership row for the active org (multi-tenant scoping).

    Clients must pass `X-Org-Id`; if missing we fall back to first membership.
    """
    memberships = await MembershipRepository(session).for_user(user.id)
    if not memberships:
        raise ForbiddenError("User has no organization membership")
    if x_org_id:
        try:
            org_uuid = UUID(x_org_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid org id"
            ) from exc
        for m in memberships:
            if m.organization_id == org_uuid:
                return m
        raise ForbiddenError("Not a member of that organization")
    return memberships[0]


CurrentMembership = Annotated[Membership, Depends(get_current_org)]


def require_roles(*allowed: MembershipRole):
    async def _checker(membership: CurrentMembership) -> Membership:
        if membership.role not in allowed:
            raise ForbiddenError(
                f"Requires role one of {[r.value for r in allowed]}"
            )
        return membership

    return _checker


# convenience
require_admin = require_roles(MembershipRole.OWNER, MembershipRole.ADMIN)
require_agent = require_roles(MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.AGENT)


async def get_organization_repo(session: DBSession) -> OrganizationRepository:
    return OrganizationRepository(session)
