"""Общие pytest-фикстуры.

Тестовая БД — отдельная (`_test`-суффикс к имени из DATABASE_URL), не та,
с которой работает `uvicorn` в dev-режиме: тесты не должны иметь возможность
стереть локальные dev-данные разработчика.

TODO(Этап 5+): фикстуры аутентифицированного клиента.
"""

from collections.abc import AsyncGenerator

import pytest
from app.core.config import get_settings
from app.core.dependencies import get_db_session
from app.database.base import Base
from app.database.models_registry import *  # noqa: F401, F403
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


def _test_database_url() -> str:
    """`.../taskflow` -> `.../taskflow_test`, сохраняя остальную часть
    DATABASE_URL — тестовая БД всегда следует за тем, что разработчик
    прописал в .env, а не захардкожена отдельной строкой, которая может
    разойтись.
    """
    base_url = get_settings().database_url
    prefix, _, db_name = base_url.rpartition("/")
    return f"{prefix}/{db_name}_test"


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Engine создаётся ЗДЕСЬ, внутри async-фикстуры, а не как module-level
    глобальная переменная. Иначе конструктор `create_async_engine()`
    отрабатывает во время сбора тестов (до того как pytest-asyncio поднимает
    event loop сессии), внутренние asyncio-примитивы пула привязываются к
    "чужому" loop, и любое реальное использование падает с
    `RuntimeError: ... attached to a different loop`. Поймано реальным
    прогоном repository-тестов, не просто по документации SQLAlchemy.
    """
    engine = create_async_engine(_test_database_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Каждый тест — в своей транзакции, откатывается в конце. Тесты не видят
    данные друг друга и не должны сами вызывать `session.commit()` для
    финальной фиксации (repository.add уже делает `flush`, этого достаточно
    для последующих SELECT внутри того же теста).
    """
    async with test_engine.connect() as connection, connection.begin() as transaction:
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """`client` теперь идёт через ту же транзакционную `db_session`, что и
    repository-тесты — не через реальный dev-engine приложения. Иначе любой
    тест, который через HTTP реально пишет в БД (register, create task, ...),
    либо засорял бы dev-базу разработчика, либо падал бы на повторный прогон
    из-за конфликта уникальности (email и т.п.). Оверрайдится ровно та
    зависимость, которую роутеры реально используют — `get_db_session`.
    """

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db_session, None)
