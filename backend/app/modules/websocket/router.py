"""WebSocket endpoint модуля.

Контракт: `WSS /ws/projects/{project_id}?token=<jwt>` (раздел 5.10).

Аутентификация и проверка доступа — вручную (try/except + `websocket.close(...)`),
не через `Depends()`, поднимающий `AppError`: обработчик `@app.exception_handler(AppError)`
в main.py применяется только к HTTP-запросам, WebSocket его не проходит —
непойманное исключение внутри WS-хендлера просто оборвёт соединение без
осмысленного кода закрытия.

`session: DbSession` — тот же `Depends(get_db_session)`, что и у HTTP-роутов
(не отдельная сессия мимо DI) — иначе тестовый override `get_db_session`
(см. tests/conftest.py) не подхватится, и WS-тесты будут стучаться в
реальную dev-БД вместо изолированной тестовой транзакции. Плата за это —
сессия держится на весь Depends()-скоуп; поскольку WS-хендлер использует её
только в начале (auth + membership check), а не в цикле сообщений, эта
плата разумна для масштаба портфолио-проекта.
"""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.dependencies import DbSession, get_current_user_ws
from app.core.exceptions import UnauthorizedError
from app.modules.projects.repository import PostgresProjectRepository
from app.modules.users.repository import PostgresUserRepository
from app.modules.websocket.connection_manager import connection_manager
from app.modules.workspace.repository import PostgresWorkspaceMemberRepository

router = APIRouter(tags=["websocket"])

# RFC 6455: 1008 = Policy Violation — ближайший стандартный код для
# "не авторизован"/"нет доступа" (HTTP 401/403 тут не применимы).
WS_POLICY_VIOLATION = 1008
# 4000-4999 — приватный диапазон приложения: "ресурс не найден".
WS_NOT_FOUND = 4004


@router.websocket("/ws/projects/{project_id}")
async def project_websocket(
    websocket: WebSocket, project_id: UUID, session: DbSession, token: str
) -> None:
    user_repository = PostgresUserRepository(session)
    try:
        user = await get_current_user_ws(token, user_repository)
    except UnauthorizedError:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    project_repository = PostgresProjectRepository(session)
    workspace_member_repository = PostgresWorkspaceMemberRepository(session)

    project = await project_repository.get_by_id(project_id)
    if project is None:
        await websocket.close(code=WS_NOT_FOUND)
        return

    membership = await workspace_member_repository.get_membership(project.workspace_id, user.id)
    if membership is None:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    await connection_manager.connect(project_id, websocket)
    try:
        while True:
            # Канал сейчас server->client (раздел 5.10) — от клиента
            # содержательных сообщений не ждём, но receive нужен, чтобы
            # обнаружить разрыв соединения через WebSocketDisconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(project_id, websocket)
