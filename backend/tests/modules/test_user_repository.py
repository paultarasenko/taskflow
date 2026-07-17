"""Repository integration tests для `users` — реальные INSERT/SELECT против
тестовой БД (см. tests/conftest.py: db_session, откатывается после теста).
"""

from app.core.security.password import hash_password
from app.modules.users.model import User
from app.modules.users.repository import PostgresUserRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    repo = PostgresUserRepository(db_session)
    user = User(
        email="alice@example.com",
        hashed_password=hash_password("s3cret-password"),
        full_name="Alice Example",
    )

    created = await repo.add(user)
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.email == "alice@example.com"
    assert fetched.full_name == "Alice Example"


async def test_get_by_email_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = PostgresUserRepository(db_session)
    result = await repo.get_by_email("nobody@example.com")
    assert result is None


async def test_get_by_email_finds_existing_user(db_session: AsyncSession) -> None:
    repo = PostgresUserRepository(db_session)
    await repo.add(
        User(
            email="bob@example.com",
            hashed_password=hash_password("another-password"),
            full_name="Bob Example",
        )
    )

    found = await repo.get_by_email("bob@example.com")

    assert found is not None
    assert found.full_name == "Bob Example"
