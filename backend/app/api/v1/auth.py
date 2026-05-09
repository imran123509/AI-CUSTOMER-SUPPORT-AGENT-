"""Authentication routes: register, login, refresh, me."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DBSession
from app.core.audit import audit_log
from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.organization import MembershipRole, Organization
from app.models.user import User
from app.repositories.organization import MembershipRepository, OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter()
settings = get_settings()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "org"


def _tokens_for(user: User, org_id: str | None = None) -> TokenResponse:
    claims = {"org_id": org_id} if org_id else None
    return TokenResponse(
        access_token=create_access_token(str(user.id), claims),
        refresh_token=create_refresh_token(str(user.id), claims),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DBSession) -> TokenResponse:
    """Create a new owner user + organization."""
    users = UserRepository(session)
    orgs = OrganizationRepository(session)
    members = MembershipRepository(session)

    if await users.get_by_email(payload.email):
        raise ConflictError("Email already registered")

    user = await users.create(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )

    base_slug = _slugify(payload.organization_name)
    slug = base_slug
    suffix = 1
    while await orgs.get_by_slug(slug):
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    org: Organization = await orgs.create(name=payload.organization_name, slug=slug)
    await members.add_member(org_id=org.id, user_id=user.id, role=MembershipRole.OWNER)
    await audit_log(
        session,
        organization_id=org.id,
        actor_id=user.id,
        action="user.registered",
        target_type="user",
        target_id=str(user.id),
    )
    await session.commit()
    return _tokens_for(user, org_id=str(org.id))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: DBSession) -> TokenResponse:
    users = UserRepository(session)
    user = await users.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account disabled")

    members = MembershipRepository(session)
    user_memberships = await members.for_user(user.id)
    org_id = str(user_memberships[0].organization_id) if user_memberships else None
    await audit_log(
        session,
        organization_id=user_memberships[0].organization_id if user_memberships else None,
        actor_id=user.id,
        action="user.login",
    )
    await session.commit()
    return _tokens_for(user, org_id=org_id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: DBSession) -> TokenResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc
    if decoded.get("type") != "refresh":
        raise UnauthorizedError("Wrong token type")
    user_id = decoded.get("sub")
    if not user_id:
        raise UnauthorizedError("Bad subject")
    user = await UserRepository(session).get(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return _tokens_for(user, org_id=decoded.get("org_id"))


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser) -> UserPublic:
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        locale=user.locale,
    )
