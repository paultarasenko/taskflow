"""Integration-тесты настроек аккаунта: профиль, смена пароля."""

from httpx import AsyncClient


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "s3cret-pass"
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Original Name"},
    )
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_update_profile_changes_full_name(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "profile-update@example.com")

    response = await client.patch(
        "/api/v1/users/me", json={"full_name": "New Name"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"

    me_response = await client.get("/api/v1/users/me", headers=headers)
    assert me_response.json()["full_name"] == "New Name"


async def test_update_profile_partial_leaves_other_fields_untouched(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "profile-partial@example.com")

    await client.patch(
        "/api/v1/users/me", json={"avatar_url": "https://example.com/a.png"}, headers=headers
    )
    response = await client.get("/api/v1/users/me", headers=headers)

    assert response.json()["full_name"] == "Original Name"
    assert response.json()["avatar_url"] == "https://example.com/a.png"


async def test_change_password_success_and_can_login_with_new_password(
    client: AsyncClient,
) -> None:
    headers = await _register_and_login(client, "pw-change@example.com", "old-password-123")

    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "old-password-123", "new_password": "new-password-456"},
        headers=headers,
    )
    assert response.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "pw-change@example.com", "password": "old-password-123"},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "pw-change@example.com", "password": "new-password-456"},
    )
    assert new_login.status_code == 200


async def test_change_password_wrong_current_password_returns_401(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "pw-wrong@example.com")

    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "totally-wrong", "new_password": "new-password-456"},
        headers=headers,
    )
    assert response.status_code == 401


async def test_account_endpoints_require_authentication(client: AsyncClient) -> None:
    patch_response = await client.patch("/api/v1/users/me", json={"full_name": "X"})
    assert patch_response.status_code == 401

    password_response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "a", "new_password": "b" * 8},
    )
    assert password_response.status_code == 401
