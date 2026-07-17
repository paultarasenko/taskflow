"""Integration-тесты жизненного цикла приглашений: create -> публичный
статус -> accept, плюс границы (чужой email, дубли, повторное принятие).
"""

import sqlalchemy as sa
from app.modules.workspace.model import Invitation
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


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


async def _get_token_by_invitation_id(db_session: AsyncSession, invitation_id: str) -> str:
    """Токен намеренно не отдаётся в `InvitationRead` (см. schema.py —
    список приглашений не должен светить чужие токены всем ADMIN/OWNER
    workspace). В проде токен уходит только по email; здесь читаем его
    напрямую из той же транзакционной тестовой сессии, что использует
    `client` (см. conftest.py) — честнее, чем эмулировать несуществующий
    API.
    """
    result = await db_session.execute(sa.select(Invitation).where(Invitation.id == invitation_id))
    token: str = result.scalar_one().token
    return token


async def test_owner_creates_invitation(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-inv@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Invite Co")

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        json={"email": "invitee-inv@example.com", "role": "member"},
        headers=owner_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "invitee-inv@example.com"
    assert body["status"] == "pending"


async def test_member_cannot_create_invitation(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-inv2@example.com")
    member_headers = await _register_and_login(client, "member-inv2@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Invite Co 2")

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member-inv2@example.com", "role": "member"},
        headers=owner_headers,
    )

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        json={"email": "someone-else@example.com", "role": "member"},
        headers=member_headers,
    )
    assert response.status_code == 403


async def test_duplicate_pending_invitation_returns_409(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner-inv3@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Invite Co 3")

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        json={"email": "dup-invitee@example.com", "role": "member"},
        headers=owner_headers,
    )
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        json={"email": "dup-invitee@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert response.status_code == 409


async def test_invitee_can_accept_invitation_and_becomes_member(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await _register_and_login(client, "owner-accept@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Accept Co")

    create_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        json={"email": "invitee-accept@example.com", "role": "admin"},
        headers=owner_headers,
    )
    token = await _get_token_by_invitation_id(db_session, create_response.json()["id"])

    invitee_headers = await _register_and_login(client, "invitee-accept@example.com")

    status_response = await client.get(f"/api/v1/invitations/{token}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"
    assert status_response.json()["workspace_name"] == "Accept Co"

    accept_response = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=invitee_headers
    )
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["role"] == "admin"

    members_response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/members", headers=owner_headers
    )
    assert members_response.json()["total"] == 2

    # Повторное принятие — уже участник.
    second_accept = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=invitee_headers
    )
    assert second_accept.status_code == 409


async def test_wrong_email_cannot_accept_invitation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await _register_and_login(client, "owner-wrong@example.com")
    workspace_id = await _create_workspace(client, owner_headers, "Wrong Co")

    create_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        json={"email": "intended@example.com", "role": "member"},
        headers=owner_headers,
    )
    token = await _get_token_by_invitation_id(db_session, create_response.json()["id"])

    intruder_headers = await _register_and_login(client, "intruder@example.com")
    response = await client.post(f"/api/v1/invitations/{token}/accept", headers=intruder_headers)
    assert response.status_code == 403


async def test_get_status_of_unknown_token_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/invitations/not-a-real-token")
    assert response.status_code == 404
