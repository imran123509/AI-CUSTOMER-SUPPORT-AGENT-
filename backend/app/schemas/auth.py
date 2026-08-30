"""Auth-related Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas._types import UUIDStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    id: UUIDStr
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    locale: str = "en"

    model_config = {"from_attributes": True}
