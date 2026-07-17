"""Integration-тесты Comments API: CRUD, RBAC (автор/admin), уведомления."""

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
) -> tuple[str, str, str]:
    ws_response = await client.post(
        "/api/v1/workspaces", json={"name": "Comment Co"}, headers=owner_headers
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
        json={"project_id": project_id, "title": "Task with comments"},
        headers=owner_headers,
    )
    task_id = task_response.json()["id"]
    return workspace_id, project_id, task_id


async def test_create_comment(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner@example.com")
    _ws, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    response = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "First comment"},
        headers=owner_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["content"] == "First comment"
    assert body["edited_at"] is None


async def test_commenting_on_own_task_does_not_self_notify(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner2@example.com")
    _ws, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    await client.post(
        f"/api/v1/tasks/{task_id}/comments", json={"content": "My own task"}, headers=owner_headers
    )

    notifications = await client.get("/api/v1/notifications", headers=owner_headers)
    assert notifications.json()["total"] == 0


async def test_comment_by_other_member_notifies_task_author(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner3@example.com")
    commenter_headers = await _register_and_login(client, "commenter3@example.com")
    workspace_id, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "commenter3@example.com", "role": "member"},
        headers=owner_headers,
    )

    response = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Question about this task"},
        headers=commenter_headers,
    )
    assert response.status_code == 201, response.text

    notifications = await client.get("/api/v1/notifications", headers=owner_headers)
    body = notifications.json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "comment"
    assert body["items"][0]["related_task_id"] == task_id


async def test_list_comments_paginated(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner4@example.com")
    _ws, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    for i in range(3):
        await client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": f"Comment {i}"},
            headers=owner_headers,
        )

    response = await client.get(f"/api/v1/tasks/{task_id}/comments", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 3


async def test_author_can_edit_own_comment(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner5@example.com")
    _ws, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    create_response = await client.post(
        f"/api/v1/tasks/{task_id}/comments", json={"content": "Original"}, headers=owner_headers
    )
    comment_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/comments/{comment_id}", json={"content": "Edited"}, headers=owner_headers
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Edited"
    assert response.json()["edited_at"] is not None


async def test_non_author_non_admin_cannot_edit_comment(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner6@example.com")
    member_headers = await _register_and_login(client, "member6@example.com")
    workspace_id, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member6@example.com", "role": "member"},
        headers=owner_headers,
    )
    create_response = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Owner's comment"},
        headers=owner_headers,
    )
    comment_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/comments/{comment_id}", json={"content": "Hacked"}, headers=member_headers
    )
    assert response.status_code == 403


async def test_workspace_admin_can_delete_others_comment(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner7@example.com")
    admin_headers = await _register_and_login(client, "admin7@example.com")
    member_headers = await _register_and_login(client, "member7@example.com")
    workspace_id, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "admin7@example.com", "role": "admin"},
        headers=owner_headers,
    )
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "member7@example.com", "role": "member"},
        headers=owner_headers,
    )
    create_response = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Member's comment"},
        headers=member_headers,
    )
    comment_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/comments/{comment_id}", headers=admin_headers)
    assert response.status_code == 204

    list_response = await client.get(f"/api/v1/tasks/{task_id}/comments", headers=owner_headers)
    assert list_response.json()["total"] == 0


async def test_outsider_cannot_access_task_comments(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "comment-owner8@example.com")
    outsider_headers = await _register_and_login(client, "outsider8@example.com")
    _ws, _proj, task_id = await _setup_workspace_project_task(client, owner_headers)

    response = await client.get(f"/api/v1/tasks/{task_id}/comments", headers=outsider_headers)
    assert response.status_code == 403


async def test_comment_endpoints_require_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000/comments",
        json={"content": "x"},
    )
    assert response.status_code == 401
