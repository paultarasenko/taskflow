"""Integration-тесты CRUD API: workspace -> project -> task, через полный
HTTP-стек (client fixture). Проверяют не только "счастливый путь", но и
границы RBAC (чужой workspace недоступен).
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
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_get_workspace(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "ws-owner@example.com")

    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Acme Inc"}, headers=headers
    )
    assert create_response.status_code == 201
    workspace = create_response.json()
    assert workspace["name"] == "Acme Inc"
    assert workspace["slug"].startswith("acme-inc-")

    get_response = await client.get(f"/api/v1/workspaces/{workspace['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == workspace["id"]


async def test_list_workspaces_only_shows_own(client: AsyncClient) -> None:
    headers_a = await _register_and_login(client, "member-a@example.com")
    headers_b = await _register_and_login(client, "member-b@example.com")

    await client.post("/api/v1/workspaces", json={"name": "A Corp"}, headers=headers_a)

    response_a = await client.get("/api/v1/workspaces", headers=headers_a)
    response_b = await client.get("/api/v1/workspaces", headers=headers_b)

    assert response_a.json()["total"] == 1
    assert response_b.json()["total"] == 0


async def test_outsider_cannot_access_workspace(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner2@example.com")
    outsider_headers = await _register_and_login(client, "outsider2@example.com")

    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Private Co"}, headers=owner_headers
    )
    workspace_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/workspaces/{workspace_id}", headers=outsider_headers)
    assert response.status_code == 403


async def _create_workspace_and_project(
    client: AsyncClient, headers: dict[str, str]
) -> dict[str, str]:
    ws_response = await client.post(
        "/api/v1/workspaces", json={"name": "Project Test Co"}, headers=headers
    )
    workspace_id = ws_response.json()["id"]

    project_response = await client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace_id, "name": "Backend", "description": "API work"},
        headers=headers,
    )
    assert project_response.status_code == 201, project_response.text
    return project_response.json()


async def test_create_project_auto_provisions_board(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "pm@example.com")
    project = await _create_workspace_and_project(client, headers)

    assert project["name"] == "Backend"
    assert project["visibility"] == "workspace"

    # Задачу можно создать без явного column_id — сервис берёт первую
    # колонку автосозданной доски (см. TaskService.create).
    task_response = await client.post(
        "/api/v1/tasks",
        json={"project_id": project["id"], "title": "First task"},
        headers=headers,
    )
    assert task_response.status_code == 201, task_response.text
    assert task_response.json()["status"] == "todo"


async def test_task_crud_flow(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "dev@example.com")
    project = await _create_workspace_and_project(client, headers)

    create_response = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project["id"],
            "title": "Implement login",
            "priority": "high",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    task = create_response.json()
    assert task["priority"] == "high"
    assert task["status"] == "todo"

    list_response = await client.get(
        "/api/v1/tasks", params={"project_id": project["id"]}, headers=headers
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    get_response = await client.get(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert get_response.status_code == 200

    update_response = await client.patch(
        f"/api/v1/tasks/{task['id']}", json={"status": "in_progress"}, headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"

    delete_response = await client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert delete_response.status_code == 204

    # Soft delete — задача больше не должна отдаваться.
    after_delete = await client.get(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert after_delete.status_code == 404


async def test_invalid_status_transition_returns_422(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "qa@example.com")
    project = await _create_workspace_and_project(client, headers)

    create_response = await client.post(
        "/api/v1/tasks", json={"project_id": project["id"], "title": "Skip states"}, headers=headers
    )
    task_id = create_response.json()["id"]

    # todo -> done напрямую запрещено (см. ALLOWED_TRANSITIONS в entity.py).
    response = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"status": "done"}, headers=headers
    )
    assert response.status_code == 422


async def test_outsider_cannot_access_tasks_of_foreign_project(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, "owner3@example.com")
    outsider_headers = await _register_and_login(client, "outsider3@example.com")
    project = await _create_workspace_and_project(client, owner_headers)

    create_response = await client.post(
        "/api/v1/tasks",
        json={"project_id": project["id"], "title": "Secret task"},
        headers=owner_headers,
    )
    task_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/tasks/{task_id}", headers=outsider_headers)
    assert response.status_code == 403


async def test_task_endpoints_require_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tasks", json={"project_id": "not-even-checked", "title": "x"}
    )
    assert response.status_code == 401
