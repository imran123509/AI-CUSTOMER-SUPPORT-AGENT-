"""JWT, password hashing, token helpers."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ----------------------------- passwords -----------------------------------
def hash_password(plain: str) -> str:
    peppered = f"{plain}{_settings.password_pepper}"
    return _pwd_context.hash(peppered)


def verify_password(plain: str, hashed: str) -> bool:
    peppered = f"{plain}{_settings.password_pepper}"
    return _pwd_context.verify(peppered, hashed)


# ----------------------------- JWT tokens ----------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    expire = _now() + timedelta(minutes=_settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": _now(),
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def create_refresh_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    expire = _now() + timedelta(days=_settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": _now(),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
