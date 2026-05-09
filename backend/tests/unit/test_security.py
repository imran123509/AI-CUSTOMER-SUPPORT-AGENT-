from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_round_trip():
    h = hash_password("supersecret")
    assert verify_password("supersecret", h)
    assert not verify_password("wrong", h)


def test_jwt_round_trip():
    access = create_access_token("user-123", {"org_id": "abc"})
    decoded = decode_token(access)
    assert decoded["sub"] == "user-123"
    assert decoded["type"] == "access"
    assert decoded["org_id"] == "abc"

    refresh = create_refresh_token("user-123")
    assert decode_token(refresh)["type"] == "refresh"
