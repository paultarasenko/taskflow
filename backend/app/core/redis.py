"""Redis-клиент.

Единственное место в проекте, где создаётся Redis-подключение — по аналогии
с `database/session.py` для Postgres. Используется для Pub/Sub fan-out
WebSocket-событий между инстансами API (см. websocket/connection_manager.py);
Celery как потребитель Redis (AI-задачи) — Roadmap, Этап 10.
"""

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    """Вызывается из lifespan-обработчика main.py при остановке приложения —
    иначе пул соединений остаётся висеть до сборки мусора."""
    await redis_client.aclose()
