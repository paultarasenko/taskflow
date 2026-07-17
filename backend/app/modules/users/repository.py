"""Repository для модуля `users`."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select

from app.database.repository import BaseRepository
from app.modules.users.model import User


class UserRepository(Protocol):
    """Абстрактный интерфейс — сервисы (в т.ч. `auth`) зависят от него, не
    от Postgres-реализации напрямую (Repository Pattern, ADR-0004).
    """

    async def get_by_id(self, id_: UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def add(self, instance: User) -> User: ...


class PostgresUserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
