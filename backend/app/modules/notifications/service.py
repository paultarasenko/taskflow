"""Бизнес-логика модуля `notifications`.

Помимо публичного API (list/mark-as-read) содержит внутренние
`notify_*`-методы — их вызывают `TaskService`/`CommentService` при
назначении задачи и создании комментария (кросс-модульно через сервис, не
через чужой репозиторий напрямую — раздел 3.1). Здесь же, а не в
модулях-источниках, потому что создание Notification — это ответственность
модуля `notifications`, источники только знают "когда" уведомлять, не "как"
это записать в БД.
"""

from collections.abc import Sequence
from uuid import UUID

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.modules.notifications.model import Notification, NotificationType
from app.modules.notifications.repository import PostgresNotificationRepository
from app.modules.users.model import User


class NotificationService:
    def __init__(self, notification_repository: PostgresNotificationRepository) -> None:
        self._notifications = notification_repository

    async def list_for_user(
        self, user: User, limit: int, offset: int
    ) -> tuple[Sequence[Notification], int]:
        return await self._notifications.list_for_user(user.id, limit=limit, offset=offset)

    async def mark_as_read(self, notification_id: UUID, current_user: User) -> Notification:
        notification = await self._notifications.get_by_id(notification_id)
        if notification is None:
            raise NotFoundError(f"Уведомление {notification_id} не найдено")
        if notification.user_id != current_user.id:
            raise PermissionDeniedError("Это не ваше уведомление")

        notification.is_read = True
        return await self._notifications.save(notification)

    # --- Внутренние методы для других сервисов ---

    async def notify_task_assigned(self, user_id: UUID, task_id: UUID) -> Notification:
        return await self._notifications.add(
            Notification(user_id=user_id, type=NotificationType.ASSIGNED, related_task_id=task_id)
        )

    async def notify_new_comment(self, user_id: UUID, task_id: UUID) -> Notification:
        return await self._notifications.add(
            Notification(user_id=user_id, type=NotificationType.COMMENT, related_task_id=task_id)
        )
