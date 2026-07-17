"""Общие SQLAlchemy-примитивы, переиспользуемые моделями всех модулей.

Не самостоятельная абстракция ради абстракции — просто чтобы не повторять
`id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid4)` и
`created_at`/`deleted_at` в 15 разных model.py (см. ADR-0003 — UUID; раздел
4.2 docs/01-architecture-and-design.md — soft delete).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """UUID (не auto-increment) — обоснование в ADR-0003."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """created_at выставляется БД (`server_default=func.now()`), а не Python —
    так значение корректно и при прямых INSERT мимо ORM (seed-скрипты, будущие
    batch-джобы).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UpdatedAtMixin:
    """Отдельно от TimestampMixin: не всем таблицам (например ACTIVITY_LOG —
    append-only) нужен updated_at.
    """

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """deleted_at nullable — см. docs/01-architecture-and-design.md, 4.2:
    безвозвратное удаление задачи/проекта — плохой UX для таск-трекера.
    Репозитории фильтруют `deleted_at IS NULL` по умолчанию.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
