"""Integration-тесты WebSocket + Redis Pub/Sub.

Starlette `TestClient` (не `httpx.AsyncClient` — тот WS не поддерживает)
запускает ASGI-приложение в отдельном потоке со своим event loop.

## Найденная и исправленная проблема: cross-event-loop соединения

Первая попытка — переиспользовать транзакционную `db_session` (как в
остальных тестах, см. conftest.py) — падала с `RuntimeError: ... attached
to a different loop`: AsyncSession, открытая в loop основного теста,
недоступна из loop TestClient-потока.

Вторая попытка — обычный (не переопределённый) клиент на реальный
`app.database.session.engine`, с explicit `engine.dispose()` после каждого
WS-блока — тоже падала с той же ошибкой, только на моменте `dispose()`:
пул всё равно пытался закрыть asyncpg-соединение, физически созданное в
loop TestClient-потока, из loop основного теста. `dispose()` не устраняет
причину, только двигает момент её проявления.

Корневая причина: SQLAlchemy `AsyncAdaptedQueuePool` кэширует живые
asyncpg-соединения между чекаутами, и каждое такое соединение жёстко
привязано к тому event loop, в котором было создано. Как только на одно и
то же соединение (через общий `engine`) претендуют два разных loop'а —
любая попытка закрыть/переиспользовать его из "чужого" loop падает.

**Рабочее решение**: отдельный engine с `NullPool` (`_ws_null_pool_engine`
ниже) — NullPool вообще не кэширует соединения: каждый checkout создаёт
новое asyncpg-соединение с нуля в _текущем_ loop и закрывает его сразу по
возврату. Соединение никогда не переживает границу вызова, поэтому вопрос
"из какого it loop его закрывать" не возникает в принципе. Через
`app.dependency_overrides[get_db_session]` эта версия подставляется вместо
обычной (пуловой) на время файла — и HTTP-вызовы через `raw_client`
(основной loop), и WS через `TestClient` (loop потока) используют её
одинаково безопасно.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from app.core.config import get_settings
from app.core.dependencies import get_db_session
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

# NullPool — намеренно, см. докстринг модуля. Engine-объект сам по себе (в
# отличие от пула с кэшем живых соединений) не хранит loop-специфичного
# состояния, поэтому безопасно создать один раз на модуль.
_ws_null_pool_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
_ws_session_factory = async_sessionmaker(_ws_null_pool_engine, expire_on_commit=False)


async def _ws_override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _ws_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
def _use_null_pool_session() -> AsyncGenerator[None, None]:
    """Переопределяем `get_db_session` для всех тестов этого файла — и
    HTTP-вызовы, и WS должны идти через NullPool-версию, иначе одна половина
    трафика будет на обычном (пуловом) engine, что возвращает исходную
    проблему наполовину.
    """
    app.dependency_overrides[get_db_session] = _ws_override_get_db_session
    yield
    app.dependency_overrides.pop(get_db_session, None)


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


async def _register_and_get_token(raw_client: AsyncClient, email: str) -> str:
    await raw_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "s3cret-pass", "full_name": "Test User"},
    )
    login = await raw_client.post(
        "/api/v1/auth/login", json={"email": email, "password": "s3cret-pass"}
    )
    token: str = login.json()["access_token"]
    return token


async def _setup_workspace_and_project(raw_client: AsyncClient, token: str) -> tuple[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    ws_response = await raw_client.post(
        "/api/v1/workspaces", json={"name": f"WS Co {uuid.uuid4().hex[:6]}"}, headers=headers
    )
    workspace_id: str = ws_response.json()["id"]
    project_response = await raw_client.post(
        "/api/v1/projects", json={"workspace_id": workspace_id, "name": "P"}, headers=headers
    )
    project_id: str = project_response.json()["id"]
    return workspace_id, project_id


async def test_ws_connects_with_valid_token_and_membership() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as raw_client:
        token = await _register_and_get_token(raw_client, _unique_email("ws-connect"))
        _workspace_id, project_id = await _setup_workspace_and_project(raw_client, token)

    test_client = TestClient(app)
    with test_client.websocket_connect(f"/ws/projects/{project_id}?token={token}") as websocket:
        assert websocket is not None


async def test_ws_rejects_invalid_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as raw_client:
        token = await _register_and_get_token(raw_client, _unique_email("ws-badtoken"))
        _workspace_id, project_id = await _setup_workspace_and_project(raw_client, token)

    test_client = TestClient(app)
    try:
        with test_client.websocket_connect(
            f"/ws/projects/{project_id}?token=not-a-real-token"
        ) as websocket:
            websocket.receive_text()
        raised = False
    except Exception:
        raised = True
    assert raised, "ожидалось закрытие соединения при невалидном токене"


async def test_ws_rejects_non_member() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as raw_client:
        owner_token = await _register_and_get_token(raw_client, _unique_email("ws-owner"))
        _workspace_id, project_id = await _setup_workspace_and_project(raw_client, owner_token)
        outsider_token = await _register_and_get_token(raw_client, _unique_email("ws-outsider"))

    test_client = TestClient(app)
    try:
        with test_client.websocket_connect(
            f"/ws/projects/{project_id}?token={outsider_token}"
        ) as websocket:
            websocket.receive_text()
        raised = False
    except Exception:
        raised = True
    assert raised, "посторонний не должен подключаться к комнате проекта"


async def test_ws_receives_task_created_event() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as raw_client:
        token = await _register_and_get_token(raw_client, _unique_email("ws-event"))
        _workspace_id, project_id = await _setup_workspace_and_project(raw_client, token)

        test_client = TestClient(app)
        with test_client.websocket_connect(f"/ws/projects/{project_id}?token={token}") as websocket:
            # Дать _subscribe_loop время реально подписаться на Redis-канал
            # до публикации события — иначе гонка (publish раньше subscribe).
            await asyncio.sleep(0.3)

            create_response = await raw_client.post(
                "/api/v1/tasks",
                json={"project_id": project_id, "title": "Realtime task"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert create_response.status_code == 201

            message = websocket.receive_json()

    assert message["type"] == "task.created"
    assert message["payload"]["title"] == "Realtime task"


async def test_ws_events_isolated_by_project() -> None:
    """Событие в проекте A не должно долетать до клиента, подключённого к
    проекту B — комнаты изолированы по project_id.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as raw_client:
        token = await _register_and_get_token(raw_client, _unique_email("ws-isolation"))
        _ws_a, project_a = await _setup_workspace_and_project(raw_client, token)
        _ws_b, project_b = await _setup_workspace_and_project(raw_client, token)

        test_client = TestClient(app)
        with test_client.websocket_connect(f"/ws/projects/{project_b}?token={token}") as ws_b:
            await asyncio.sleep(0.3)

            await raw_client.post(
                "/api/v1/tasks",
                json={"project_id": project_a, "title": "Task in project A"},
                headers={"Authorization": f"Bearer {token}"},
            )
            # Сигнальное событие в СВОЁМ проекте — если оно дошло, а из
            # project_a ничего не пришло раньше него, значит изоляция
            # работает (иначе первым получили бы событие из project_a).
            await raw_client.post(
                "/api/v1/tasks",
                json={"project_id": project_b, "title": "Task in project B"},
                headers={"Authorization": f"Bearer {token}"},
            )

            message = ws_b.receive_json()

    assert message["payload"]["title"] == "Task in project B"
