"""Базовый generic-репозиторий.

Не абстракция ради абстракции: 7 модулей (users, workspace, projects, tasks,
comments, notifications, ai) владеют моделями и почти всем нужен один и тот
же набор операций (get_by_id, list, add, delete-с-учётом-soft-delete).
Вынесено сюда один раз, конкретные репозитории модулей добавляют только
доменные запросы (например `UserRepository.get_by_email`), а не
переизобретают `SELECT ... WHERE id = :id` в каждом модуле.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository[ModelType]:
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(self) -> Select[tuple[ModelType]]:
        stmt = select(self.model)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    async def get_by_id(self, id_: UUID) -> ModelType | None:
        stmt = self._base_query().where(self.model.id == id_)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int) -> tuple[Sequence[ModelType], int]:
        """Возвращает (items, total). Оборачивание в PaginatedResponse —
        забота router/service-слоя, репозиторий не знает про API-контракт
        (см. app/core/pagination.py).
        """
        count_stmt = select(func.count()).select_from(self._base_query().subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = self._base_query().limit(limit).offset(offset)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        await self.session.flush()  # получить id/server_default до commit
        return instance

    async def save(self, instance: ModelType) -> ModelType:
        """Для уже персистентного объекта, изменённого in-place (SQLAlchemy
        отслеживает изменения атрибутов сам — `flush()` просто проталкивает
        их в БД раньше общего commit на границе запроса). Отдельно от `add`,
        чтобы намерение в коде сервиса читалось явно: "сохранить изменения",
        а не "создать новую запись".
        """
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Soft delete, если модель поддерживает — иначе настоящий DELETE.
        Ассоциативные таблицы (TaskAssignee, TaskTag) не имеют deleted_at,
        для них это единственный сценарий и есть.
        """
        if hasattr(instance, "deleted_at"):
            instance.deleted_at = datetime.now(UTC)
        else:
            await self.session.delete(instance)
        await self.session.flush()
