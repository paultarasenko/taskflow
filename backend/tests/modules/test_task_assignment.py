"""Integration-тесты назначения исполнителя на задачу + создание Notification."""

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


async def _setup_workspace_project_task(
    client: AsyncClient, owner_headers: dict[str, str]
) -> tuple[str, str]:
    ws_response = await client.post(
        "/api/v1/workspaces", json={"name": "Assign Co"}, headers=owner_headers
    )
    workspace_id = ws_response.json()["id"]

    project_response = await client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace_id, "name": "Backend"},
        headers=owner_headers,
    )
    project_id = project_response.json()["id"]

    task_response = await client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Do the thing"},
        headers=owner_headers,
    )
    task_id = task_response.json()["id"]
    return workspace_id, task_id


async def test_assign_task_creates_notification_for_assignee(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "assign-owner@example.com")
    assignee_headers = await _register_and_login(client, "assignee@example.com")
    workspace_id, task_id = await _setup_workspace_project_task(client, owner_headers)

    me_response = await client.get("/api/v1/users/me", headers=assignee_headers)
    assignee_id = me_response.json()["id"]

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "assignee@example.com", "role": "member"},
        headers=owner_headers,
    )

    assign_response = await client.post(
        f"/api/v1/tasks/{task_id}/assignees",
        json={"user_id": assignee_id},
        headers=owner_headers,
    )
    assert assign_response.status_code == 201, assign_response.text
    assert assign_response.json()["user_id"] == assignee_id

    notifications_response = await client.get("/api/v1/notifications", headers=assignee_headers)
    assert notifications_response.status_code == 200
    body = notifications_response.json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "assigned"
    assert body["items"][0]["related_task_id"] == task_id
    assert body["items"][0]["is_read"] is False


async def test_cannot_assign_task_to_non_workspace_member(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "assign-owner2@example.com")
    outsider_headers = await _register_and_login(client, "outsider-assign@example.com")
    _workspace_id, task_id = await _setup_workspace_project_task(client, owner_headers)

    outsider_me = await client.get("/api/v1/users/me", headers=outsider_headers)
    outsider_id = outsider_me.json()["id"]

    response = await client.post(
        f"/api/v1/tasks/{task_id}/assignees",
        json={"user_id": outsider_id},
        headers=owner_headers,
    )
    assert response.status_code == 403


async def test_duplicate_assignment_returns_409(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "assign-owner3@example.com")
    assignee_headers = await _register_and_login(client, "assignee3@example.com")
    workspace_id, task_id = await _setup_workspace_project_task(client, owner_headers)

    assignee_me = await client.get("/api/v1/users/me", headers=assignee_headers)
    assignee_id = assignee_me.json()["id"]

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "assignee3@example.com", "role": "member"},
        headers=owner_headers,
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/assignees", json={"user_id": assignee_id}, headers=owner_headers
    )
    response = await client.post(
        f"/api/v1/tasks/{task_id}/assignees", json={"user_id": assignee_id}, headers=owner_headers
    )
    assert response.status_code == 409


async def test_mark_notification_as_read(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "assign-owner4@example.com")
    assignee_headers = await _register_and_login(client, "assignee4@example.com")
    workspace_id, task_id = await _setup_workspace_project_task(client, owner_headers)

    assignee_me = await client.get("/api/v1/users/me", headers=assignee_headers)
    assignee_id = assignee_me.json()["id"]

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "assignee4@example.com", "role": "member"},
        headers=owner_headers,
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/assignees", json={"user_id": assignee_id}, headers=owner_headers
    )

    notifications = await client.get("/api/v1/notifications", headers=assignee_headers)
    notification_id = notifications.json()["items"][0]["id"]

    read_response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=assignee_headers
    )
    assert read_response.status_code == 200
    assert read_response.json()["is_read"] is True


async def test_cannot_mark_others_notification_as_read(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "assign-owner5@example.com")
    assignee_headers = await _register_and_login(client, "assignee5@example.com")
    intruder_headers = await _register_and_login(client, "intruder5@example.com")
    workspace_id, task_id = await _setup_workspace_project_task(client, owner_headers)

    assignee_me = await client.get("/api/v1/users/me", headers=assignee_headers)
    assignee_id = assignee_me.json()["id"]

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "assignee5@example.com", "role": "member"},
        headers=owner_headers,
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/assignees", json={"user_id": assignee_id}, headers=owner_headers
    )

    notifications = await client.get("/api/v1/notifications", headers=assignee_headers)
    notification_id = notifications.json()["items"][0]["id"]

    response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=intruder_headers
    )
    assert response.status_code == 403
