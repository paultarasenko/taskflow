"""Async engine + session factory.

Единственное место в проекте, где создаётся SQLAlchemy engine — репозитории
получают сессию только через `get_db_session` (app/core/dependencies.py),
никогда не создают свою.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug and settings.environment == "local",
    pool_pre_ping=True,  # переживает разрыв соединения с Postgres после простоя
)

session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,  # объекты остаются доступны после commit (нужны в response)
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Session-per-request с автоматическим commit/rollback.

    Сервисы не обязаны помнить про `session.commit()` в каждом юзкейсе:
    успешный запрос коммитится здесь один раз в конце, исключение — откатывает.
    Если юзкейсу нужен более гранулярный контроль (например, промежуточный
    commit), он делает это явно внутри — эта обвязка не мешает.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
