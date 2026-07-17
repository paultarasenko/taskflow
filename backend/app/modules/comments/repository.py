"""Repository для модуля `comments`."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select

from app.database.repository import BaseRepository
from app.modules.comments.model import Comment


class CommentRepository(Protocol):
    async def get_by_id(self, id_: UUID) -> Comment | None: ...
    async def list_by_task(
        self, task_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Comment], int]: ...
    async def add(self, instance: Comment) -> Comment: ...


class PostgresCommentRepository(BaseRepository[Comment]):
    model = Comment

    async def list_by_task(
        self, task_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Comment], int]:
        stmt = select(Comment).where(Comment.task_id == task_id)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Comment.created_at).limit(limit).offset(offset)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
