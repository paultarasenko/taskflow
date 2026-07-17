"""Repository для модуля `notifications`."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select

from app.database.repository import BaseRepository
from app.modules.notifications.model import Notification


class NotificationRepository(Protocol):
    async def get_by_id(self, id_: UUID) -> Notification | None: ...
    async def list_for_user(
        self, user_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Notification], int]: ...
    async def add(self, instance: Notification) -> Notification: ...


class PostgresNotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self, user_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
