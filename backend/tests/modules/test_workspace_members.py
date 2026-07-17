"""Integration-тесты управления участниками workspace (RBAC через
require_workspace_role) — полный HTTP-стек, изолированная БД.
"""

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "s3cret-pass", "full_name": "Test User"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "s3cret-pass"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_workspace(client: AsyncClient, headers: dict[str, str], name: str) -> str:
    response = await client.post("/api/v1/workspaces", json={"name": name}, headers=headers)
    workspace_id: str = response.json()["id"]
    return workspace_id


async def test_owner_can_add_existing_user_as_member(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-add@example.com")
    await _register_and_login(client, "invitee-add@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Acme")

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "invitee-add@example.com", "role": "member"},
        headers=owner_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "member"
    assert body["user"]["email"] == "invitee-add@example.com"


async def test_add_member_for_unregistered_email_returns_404(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-add2@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Acme2")

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "nobody-registered@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert response.status_code == 404


async def test_member_cannot_add_other_members(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-rbac@example.com")
    member_headers = await _register_and_login(client, "member-rbac@example.com")
    await _register_and_login(client, "outsider-rbac@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "RBAC Co")

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member-rbac@example.com", "role": "member"},
        headers=owner_headers,
    )

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "outsider-rbac@example.com", "role": "member"},
        headers=member_headers,
    )
    assert response.status_code == 403


async def test_owner_can_list_members(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-list@example.com")
    await _register_and_login(client, "member-list@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "List Co")

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member-list@example.com", "role": "member"},
        headers=owner_headers,
    )

    response = await client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2  # owner + добавленный member


async def test_owner_can_change_member_role(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-role@example.com")
    await _register_and_login(client, "member-role@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Role Co")

    add_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member-role@example.com", "role": "member"},
        headers=owner_headers,
    )
    user_id = add_response.json()["user"]["id"]

    response = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{user_id}",
        json={"role": "admin"},
        headers=owner_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_member_cannot_change_roles(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-role2@example.com")
    member_headers = await _register_and_login(client, "member-role2@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Role Co 2")

    add_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member-role2@example.com", "role": "member"},
        headers=owner_headers,
    )
    user_id = add_response.json()["user"]["id"]

    response = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{user_id}",
        json={"role": "admin"},
        headers=member_headers,
    )
    assert response.status_code == 403


async def test_cannot_change_owner_role(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-protect@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Protect Co")

    me_response = await client.get("/api/v1/users/me", headers=owner_headers)
    owner_user_id = me_response.json()["id"]

    response = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{owner_user_id}",
        json={"role": "member"},
        headers=owner_headers,
    )
    assert response.status_code == 403


async def test_owner_can_remove_member(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-remove@example.com")
    await _register_and_login(client, "member-remove@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Remove Co")

    add_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member-remove@example.com", "role": "member"},
        headers=owner_headers,
    )
    user_id = add_response.json()["user"]["id"]

    response = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{user_id}", headers=owner_headers
    )
    assert response.status_code == 204

    list_response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/members", headers=owner_headers
    )
    assert list_response.json()["total"] == 1


async def test_member_can_remove_self(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-leave@example.com")
    member_headers = await _register_and_login(client, "member-leave@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Leave Co")

    add_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member-leave@example.com", "role": "member"},
        headers=owner_headers,
    )
    user_id = add_response.json()["user"]["id"]

    response = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{user_id}", headers=member_headers
    )
    assert response.status_code == 204


async def test_owner_cannot_be_removed(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-noremove@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "NoRemove Co")

    me_response = await client.get("/api/v1/users/me", headers=owner_headers)
    owner_user_id = me_response.json()["id"]

    response = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{owner_user_id}", headers=owner_headers
    )
    assert response.status_code == 403
