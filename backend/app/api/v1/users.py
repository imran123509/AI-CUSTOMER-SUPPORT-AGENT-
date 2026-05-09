"""User profile routes."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import UserPublic

router = APIRouter()


@router.get("/me", response_model=UserPublic)
async def get_me(user: CurrentUser) -> UserPublic:
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        locale=user.locale,
    )


@router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: dict,
    user: CurrentUser,
    session: DBSession,
) -> UserPublic:
    if "full_name" in payload and payload["full_name"]:
        user.full_name = payload["full_name"]
    if "locale" in payload and payload["locale"]:
        user.locale = payload["locale"]
    if "avatar_url" in payload:
        user.avatar_url = payload["avatar_url"]
    await session.commit()
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        locale=user.locale,
    )
