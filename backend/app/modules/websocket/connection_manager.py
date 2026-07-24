"""Connection manager для WebSocket-соединений.

Отклонение от стандартного шаблона модуля (см. docs/01-architecture-and-design.md,
раздел 3): у `websocket` нет `model.py` — модуль не владеет персистентными данными,
только держит активные соединения в памяти процесса и делает fan-out через Redis
Pub/Sub между инстансами API. Поэтому `repository.py` заменён на `connection_manager.py`
— по смыслу это тот же "доступ к ресурсу", только ресурс не в Postgres, а in-memory.

Единственный экземпляр на процесс (`connection_manager` внизу файла) — не
создаётся через FastAPI `Depends()` каждый запрос, а держит живое состояние
(активные WS-соединения, задачи подписки на Redis) на весь жизненный цикл
приложения.
"""

import asyncio
import logging
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket
from redis.asyncio import Redis

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Комната = `project_id`. На каждый проект с хотя бы одним локальным
    WS-клиентом на этом инстансе — ровно одна Redis pub/sub подписка
    (`_subscriptions`), которая рассылает всем локальным клиентам этой
    комнаты. `publish()` всегда идёт через Redis, даже если публикующий и
    получатель на одном инстансе — единый код-путь независимо от того,
    сколько сейчас реплик API (раздел 2.3 архитектурного документа: "Redis
    Pub/Sub — горизонтальное масштабирование WS без sticky sessions").
    """

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client
        self._local_connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._subscriptions: dict[UUID, asyncio.Task[None]] = {}

    @staticmethod
    def _channel(project_id: UUID) -> str:
        return f"project:{project_id}"

    async def connect(self, project_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._local_connections[project_id].add(websocket)

        if project_id not in self._subscriptions:
            self._subscriptions[project_id] = asyncio.create_task(self._subscribe_loop(project_id))

    async def disconnect(self, project_id: UUID, websocket: WebSocket) -> None:
        connections = self._local_connections.get(project_id)
        if connections is None:
            return
        connections.discard(websocket)

        if not connections:
            del self._local_connections[project_id]
            task = self._subscriptions.pop(project_id, None)
            if task is not None:
                task.cancel()

    async def publish(self, project_id: UUID, message: str) -> None:
        """Публикует в Redis — подхватят все инстансы (в т.ч. этот же,
        через собственный `_subscribe_loop`), не только текущие локальные
        соединения. Вызывается из TaskService/CommentService при изменениях.
        """
        await self._redis.publish(self._channel(project_id), message)

    async def _subscribe_loop(self, project_id: UUID) -> None:
        """Живёт, пока у комнаты есть хотя бы один локальный клиент —
        отменяется в `disconnect()`, когда уходит последний.
        """
        pubsub = self._redis.pubsub()
        channel = self._channel(project_id)
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                await self._broadcast_local(project_id, message["data"])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            # redis-py: aclose() без типов в установленной версии стабов.
            await pubsub.aclose()  # type: ignore[no-untyped-call]

    async def _broadcast_local(self, project_id: UUID, data: str) -> None:
        connections = list(self._local_connections.get(project_id, set()))
        for websocket in connections:
            try:
                await websocket.send_text(data)
            except (
                Exception
            ):  # noqa: BLE001 — одно упавшее соединение не должно рвать рассылку остальным
                logger.debug("Не удалось отправить сообщение WS-клиенту, отключаю", exc_info=True)
                self._local_connections[project_id].discard(websocket)


# Единственный экземпляр на процесс — см. докстринг класса. Использует тот
# же Redis-клиент, что и остальное приложение (app/core/redis.py).
connection_manager = ConnectionManager(redis_client)
