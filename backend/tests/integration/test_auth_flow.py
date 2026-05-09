import pytest


@pytest.mark.asyncio
async def test_register_login_me(client):
    payload = {
        "email": "alice@demo.unfyd.io",
        "password": "Demo1234!",
        "full_name": "Alice Tester",
        "organization_name": "Demo Co",
    }
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    tokens = r.json()
    assert "access_token" in tokens

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert r.status_code == 200
    access = r.json()["access_token"]

    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == payload["email"]
