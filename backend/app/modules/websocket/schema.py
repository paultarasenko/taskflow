"""Схемы WebSocket-событий (server -> client).

Список событий зафиксирован в docs/01-architecture-and-design.md, раздел 5.10:
task.created, task.updated, task.moved, task.deleted, comment.created,
notification.created, member.online/offline.

Все события — один и тот же конверт `WSEvent{type, payload}`, а не разные
Pydantic-модели на каждый тип: клиенту всё равно нужно диспетчеризовать по
`type` на своей стороне, отдельная модель на событие добавила бы только
формальную типизацию без практической пользы на этой стороне (сервер их не
парсит обратно, только сериализует).
"""

import enum
from typing import Any

from pydantic import BaseModel


class WSEventType(enum.StrEnum):
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_MOVED = "task.moved"
    TASK_DELETED = "task.deleted"
    COMMENT_CREATED = "comment.created"
    NOTIFICATION_CREATED = "notification.created"
    MEMBER_ONLINE = "member.online"
    MEMBER_OFFLINE = "member.offline"


class WSEvent(BaseModel):
    type: WSEventType
    payload: dict[str, Any]
