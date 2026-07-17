"""Тест подключения к PostgreSQL через реальный engine приложения."""

from app.database.session import engine
from sqlalchemy import text


async def test_database_connection_is_alive() -> None:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
