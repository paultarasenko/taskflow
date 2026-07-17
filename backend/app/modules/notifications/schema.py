"""Pydantic DTO модуля `notifications`."""

from uuid import UUID

from app.modules.notifications.model import NotificationType
from app.shared.schemas import IDMixin, ORMModel, TimestampMixin


class NotificationRead(ORMModel, IDMixin, TimestampMixin):
    user_id: UUID
    type: NotificationType
    related_task_id: UUID | None
    is_read: bool
