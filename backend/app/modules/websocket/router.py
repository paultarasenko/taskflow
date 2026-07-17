"""WebSocket endpoint модуля.

Контракт: `WSS /ws/projects/{project_id}?token=<jwt>` (раздел 5.10).
TODO(Этап 8): реализация.
"""

from fastapi import APIRouter

router = APIRouter(tags=["websocket"])

# Эндпоинт появится на Этапе 8.
