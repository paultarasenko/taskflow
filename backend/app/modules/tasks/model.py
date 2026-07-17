"""SQLAlchemy-модели модуля `tasks`: Board, Column, Task, TaskAssignee, Tag,
TaskTag, ActivityLog.

Модуль owns все Kanban-сущности целиком (см. docs/01-architecture-and-design.md,
раздел 3 — таблица модулей). `ActivityLog` — единая полиморфная таблица
вместо TaskHistory (см. ADR и раздел 4.2 архитектурного документа); в MVP
её пишет только `tasks`, но `entity_type` уже рассчитан на будущий аудит
workspace/project без миграции схемы.
"""

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UpdatedAtMixin,
    UUIDPrimaryKeyMixin,
)
from app.modules.tasks.entity import TaskPriority, TaskStatus

if TYPE_CHECKING:
    from app.modules.comments.model import Comment
    from app.modules.projects.model import Project
    from app.modules.users.model import User


class Board(UUIDPrimaryKeyMixin, Base):
    """1:1 с Project (см. ERD `PROJECTS ||--|| BOARDS`). Без временных полей —
    ERD не заводит их здесь.
    """

    __tablename__ = "boards"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="board")
    columns: Mapped[list["Column"]] = relationship(
        back_populates="board", cascade="all, delete-orphan", order_by="Column.position"
    )

    def __repr__(self) -> str:
        return f"<Board id={self.id} project_id={self.project_id}>"


class Column(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "columns"

    board_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wip_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    board: Mapped["Board"] = relationship(back_populates="columns")
    tasks: Mapped[list["Task"]] = relationship(back_populates="column", order_by="Task.position")

    def __repr__(self) -> str:
        return f"<Column id={self.id} name={self.name!r} position={self.position}>"


class Task(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, SoftDeleteMixin, Base):
    __tablename__ = "tasks"

    column_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("columns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.TODO, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority"), nullable=False, default=TaskPriority.MEDIUM
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    column: Mapped["Column"] = relationship(back_populates="tasks")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])
    assignees: Mapped[list["TaskAssignee"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    tags: Mapped[list["TaskTag"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"


class TaskAssignee(Base):
    """Чистая association-таблица — в ERD нет собственного `id` (композитный
    PK task_id+user_id), в отличие от WORKSPACE_MEMBERS/PROJECT_MEMBERS.
    """

    __tablename__ = "task_assignees"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)

    task: Mapped["Task"] = relationship(back_populates="assignees")
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<TaskAssignee task_id={self.task_id} user_id={self.user_id}>"


class Tag(UUIDPrimaryKeyMixin, Base):
    """Без временных полей — ERD их не заводит для TAGS."""

    __tablename__ = "tags"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6B7280")

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name!r}>"


class TaskTag(Base):
    """Association-таблица, композитный PK — как TaskAssignee."""

    __tablename__ = "task_tags"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

    task: Mapped["Task"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()


class ActivityEntityType(enum.StrEnum):
    TASK = "task"
    PROJECT = "project"
    WORKSPACE = "workspace"


class ActivityLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only — нет UpdatedAtMixin намеренно, запись истории не
    редактируется. `entity_id` без FK-констрейнта: поле полиморфное
    (task|project|workspace), обычный FK на одну таблицу тут невозможен —
    целостность обеспечивается на уровне сервиса, не БД (см. раздел 4.2).
    """

    __tablename__ = "activity_log"

    entity_type: Mapped[ActivityEntityType] = mapped_column(
        Enum(ActivityEntityType, name="activity_entity_type"), nullable=False, index=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    actor: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<ActivityLog {self.entity_type}:{self.entity_id} {self.field_name}>"
