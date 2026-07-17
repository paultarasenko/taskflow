"""Pydantic DTO модуля `tasks`."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.tasks.entity import TaskPriority, TaskStatus
from app.shared.schemas import IDMixin, ORMModel, TimestampMixin


class TaskCreate(BaseModel):
    project_id: UUID
    column_id: UUID | None = None
    """None -> сервис берёт первую колонку доски проекта по `position`
    (см. TaskService.create) — своих board/column-эндпоинтов в этом шаге
    ещё нет (Kanban UI — Этап 9), а создавать задачу нужно уже сейчас."""
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class TaskUpdate(BaseModel):
    """Все поля опциональны — PATCH, не PUT: обновляются только переданные."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    column_id: UUID | None = None


class TaskRead(ORMModel, IDMixin, TimestampMixin):
    project_id: UUID
    column_id: UUID
    title: str
    description: str | None
    author_id: UUID
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    position: int


class TaskAssigneeCreate(BaseModel):
    user_id: UUID


class TaskAssigneeRead(ORMModel):
    """Не IDMixin — TaskAssignee композитный PK (task_id+user_id),
    без своего `id` (см. ADR/раздел 4.1, TASK_ASSIGNEES без отдельного id)."""

    task_id: UUID
    user_id: UUID
