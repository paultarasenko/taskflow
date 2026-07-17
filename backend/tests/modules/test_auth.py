"""Integration-тесты аутентификации через полный HTTP-стек (client fixture,
изолированная транзакционная БД — см. tests/conftest.py).
"""

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "alice@example.com") -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "s3cret-pass", "full_name": "Alice Example"},
    )
    assert response.status_code == 201, response.text


async def test_register_creates_user_without_leaking_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "s3cret-pass", "full_name": "Bob Example"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "bob@example.com"
    assert body["full_name"] == "Bob Example"
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    await _register(client, "carol@example.com")

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "another-pass", "full_name": "Carol 2"},
    )

    assert response.status_code == 409


async def test_login_success_returns_access_token(client: AsyncClient) -> None:
    await _register(client, "dave@example.com")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "s3cret-pass"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await _register(client, "erin@example.com")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "erin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_me_with_valid_token_returns_current_user(client: AsyncClient) -> None:
    await _register(client, "frank@example.com")
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "frank@example.com", "password": "s3cret-pass"},
    )
    token = login_response.json()["access_token"]

    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "frank@example.com"


async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_me_with_garbage_token_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
