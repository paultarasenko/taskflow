"""Repository integration tests для `workspace` — включая soft delete."""

from app.core.security.password import hash_password
from app.core.security.permissions import WorkspaceRole
from app.modules.users.model import User
from app.modules.workspace.model import Workspace, WorkspaceMember
from app.modules.workspace.repository import (
    PostgresWorkspaceMemberRepository,
    PostgresWorkspaceRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_user(db_session: AsyncSession, email: str) -> User:
    user = User(email=email, hashed_password=hash_password("x"), full_name="Test User")
    db_session.add(user)
    await db_session.flush()
    return user


async def test_list_for_user_returns_only_workspaces_user_belongs_to(
    db_session: AsyncSession,
) -> None:
    owner = await _make_user(db_session, "owner@example.com")
    outsider = await _make_user(db_session, "outsider@example.com")

    ws_repo = PostgresWorkspaceRepository(db_session)
    member_repo = PostgresWorkspaceMemberRepository(db_session)

    workspace = await ws_repo.add(Workspace(name="Acme", slug="acme", owner_id=owner.id))
    await member_repo.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER)
    )

    owner_workspaces, owner_total = await ws_repo.list_for_user(owner.id, limit=50, offset=0)
    outsider_workspaces, outsider_total = await ws_repo.list_for_user(
        outsider.id, limit=50, offset=0
    )

    assert [w.slug for w in owner_workspaces] == ["acme"]
    assert list(outsider_workspaces) == []


async def test_soft_deleted_workspace_excluded_from_get_by_id(
    db_session: AsyncSession,
) -> None:
    owner = await _make_user(db_session, "owner2@example.com")
    repo = PostgresWorkspaceRepository(db_session)
    workspace = await repo.add(Workspace(name="Temp", slug="temp", owner_id=owner.id))

    await repo.delete(workspace)  # soft delete — BaseRepository видит deleted_at

    assert await repo.get_by_id(workspace.id) is None
