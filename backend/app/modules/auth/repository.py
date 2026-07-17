"""Repository interface + Postgres-реализация модуля `auth`.

Протокол фиксируется здесь ещё до появления Postgres-реализации, чтобы
service.py с самого начала зависел от абстракции, а не от SQLAlchemy
напрямую (Repository Pattern, см. ADR-0004).

TODO(Этап 5): реализовать.
"""

from typing import Protocol


class AuthRepository(Protocol):
    """Абстрактный интерфейс репозитория — реализация появится на Этапе 5."""

    ...


class PostgresAuthRepository:
    """Конкретная реализация поверх SQLAlchemy AsyncSession. TODO(Этап 5)."""

    ...
