"""Доказательство того, что скелет приложения реально запускается.

Не заглушка: этот тест по-настоящему поднимает FastAPI app через ASGI
transport и бьёт по /health. Проходит уже на Этапе 2, до появления БД.
"""

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_ready_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200


async def test_openapi_schema_is_generated(client: AsyncClient) -> None:
    """Проверяет, что все роутеры модулей подключились без ошибок импорта."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "TaskFlow API"
