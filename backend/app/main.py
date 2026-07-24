"""Точка входа приложения.

На Этапе 2 задача этого файла — доказать, что скелет реально запускается:
`uvicorn app.main:app` поднимает сервер, `/health` отвечает 200, все роутеры
модулей подключены (даже если внутри пока нет эндпоинтов). Реальная бизнес-
логика подключается по мере готовности модулей на следующих этапах.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.exceptions import AppError, ProblemDetail
from app.core.redis import close_redis, redis_client

# Импорт до роутеров: гарантирует, что SQLAlchemy registry знает обо всех
# моделях до первого запроса — иначе строковые relationship-таргеты
# (`Mapped[list["Comment"]]` и т.п.) могут не резолвиться при первом
# обращении к ORM (см. app/database/models_registry.py, там же история бага).
from app.database.models_registry import *  # noqa: F401, F403
from app.database.session import engine
from app.modules.ai.router import router as ai_router
from app.modules.auth.router import router as auth_router
from app.modules.comments.router import router as comments_router
from app.modules.notifications.router import router as notifications_router
from app.modules.projects.router import router as projects_router
from app.modules.tasks.router import router as tasks_router
from app.modules.users.router import router as users_router
from app.modules.websocket.router import router as websocket_router
from app.modules.workspace.router import invitation_router as workspace_invitation_router
from app.modules.workspace.router import router as workspace_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        problem = ProblemDetail(
            type=exc.error_type,
            title=exc.error_type.replace("-", " ").title(),
            status=exc.status_code,
            detail=exc.detail,
            instance=str(request.url.path),
        )
        return JSONResponse(status_code=exc.status_code, content=problem.model_dump())

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"], response_model=None)
    async def health_ready() -> dict[str, str] | JSONResponse:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 — health-check обязан пережить любую ошибку БД
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "detail": f"database: {exc}"},
            )

        try:
            await redis_client.ping()
        except Exception as exc:  # noqa: BLE001 — health-check обязан пережить любую ошибку Redis
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "detail": f"redis: {exc}"},
            )

        return {"status": "ok"}

    api_prefix = settings.api_v1_prefix
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(workspace_router, prefix=api_prefix)
    app.include_router(workspace_invitation_router, prefix=api_prefix)
    app.include_router(projects_router, prefix=api_prefix)
    app.include_router(tasks_router, prefix=api_prefix)
    app.include_router(comments_router, prefix=api_prefix)
    app.include_router(notifications_router, prefix=api_prefix)
    app.include_router(ai_router, prefix=api_prefix)
    app.include_router(websocket_router)  # WS-эндпоинт без /api/v1 префикса

    return app


app = create_app()
