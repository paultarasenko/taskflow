"""Repository для модуля `tasks`: Task, Board, Column, Tag, ActivityLog.

Возвращает ORM-модели, не TaskEntity — маппинг в доменную сущность (см.
entity.py, ADR-0004) подключается на Этапе 7 вместе с TaskService, где он
реально используется. Заводить его здесь заранее без потребителя было бы
той самой "абстракцией ради абстракции", которой правило ADR-0004 просило
избегать.
"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select

from app.database.repository import BaseRepository
from app.modules.tasks.entity import TaskPriority, TaskStatus
from app.modules.tasks.model import ActivityLog, Board, Column, Tag, Task, TaskAssignee


class TaskRepository(Protocol):
    async def get_by_id(self, id_: UUID) -> Task | None: ...
    async def list_by_project(
        self,
        project_id: UUID,
        limit: int,
        offset: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
    ) -> tuple[Sequence[Task], int]: ...
    async def add(self, instance: Task) -> Task: ...


class PostgresTaskRepository(BaseRepository[Task]):
    model = Task

    async def list_by_project(
        self,
        project_id: UUID,
        limit: int,
        offset: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
    ) -> tuple[Sequence[Task], int]:
        """Реализует контракт `GET /projects/{id}/tasks?status=&priority=&limit=&offset=`
        из docs/01-architecture-and-design.md, раздел 5.5. `q`/`tags`/`sort`
        добавятся вместе с UI-фильтрами на Этапе 7 — не нужны репозиторию,
        пока их некому передать.
        """
        stmt = self._base_query().where(Task.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Task.position).limit(limit).offset(offset)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total


class PostgresBoardRepository(BaseRepository[Board]):
    model = Board

    async def get_by_project(self, project_id: UUID) -> Board | None:
        stmt = select(Board).where(Board.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PostgresColumnRepository(BaseRepository[Column]):
    model = Column

    async def list_by_board(self, board_id: UUID) -> Sequence[Column]:
        stmt = select(Column).where(Column.board_id == board_id).order_by(Column.position)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PostgresTagRepository(BaseRepository[Tag]):
    model = Tag

    async def list_by_workspace(self, workspace_id: UUID) -> Sequence[Tag]:
        stmt = select(Tag).where(Tag.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PostgresActivityLogRepository(BaseRepository[ActivityLog]):
    model = ActivityLog

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[ActivityLog], int]:
        stmt = select(ActivityLog).where(
            ActivityLog.entity_type == entity_type, ActivityLog.entity_id == entity_id
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(ActivityLog.created_at.desc()).limit(limit).offset(offset)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total


class PostgresTaskAssigneeRepository(BaseRepository[TaskAssignee]):
    """Модель существует с Этапа 4, репозитория не было — `POST /tasks/{id}/assignees`
    был в исходном API-дизайне (раздел 5.5), но не реализовывался до Этапа 7,
    когда понадобился как триггер для уведомления о назначении.
    """

    model = TaskAssignee

    async def exists(self, task_id: UUID, user_id: UUID) -> bool:
        stmt = select(TaskAssignee).where(
            TaskAssignee.task_id == task_id, TaskAssignee.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
