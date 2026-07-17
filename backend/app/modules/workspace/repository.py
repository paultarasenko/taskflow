"""Repository для модуля `workspace`."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.database.repository import BaseRepository
from app.modules.workspace.model import Invitation, Workspace, WorkspaceMember


class WorkspaceRepository(Protocol):
    async def get_by_id(self, id_: UUID) -> Workspace | None: ...
    async def list_for_user(
        self, user_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Workspace], int]: ...
    async def add(self, instance: Workspace) -> Workspace: ...


class PostgresWorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def list_for_user(
        self, user_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Workspace], int]:
        """Workspaces, где пользователь состоит участником — join через
        WorkspaceMember, а не отдельный денормализованный список.
        """
        stmt = (
            self._base_query()
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Workspace.created_at).limit(limit).offset(offset)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total


class PostgresWorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember

    async def get_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None:
        """`selectinload(.user)` — вызывающий код (change_member_role,
        require_workspace_member) может отдать результат напрямую через
        `WorkspaceMemberRead.model_validate(...)`, а `.user` — обязательное
        поле схемы. Без eager load обращение к `.user` в Pydantic-валидации
        (синхронный контекст) падает с `MissingGreenlet` — async-ленивая
        подгрузка требует активного awaited-контекста, которого там нет.
        """
        stmt = (
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self, workspace_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[WorkspaceMember], int]:
        """`selectinload(.user)` — список участников почти всегда отдаётся
        вместе с их email/именем (см. WorkspaceMemberRead), без eager load
        это был бы N+1 на каждый member в списке.
        """
        stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.options(selectinload(WorkspaceMember.user))
            .order_by(WorkspaceMember.joined_at)
            .limit(limit)
            .offset(offset)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total


class PostgresInvitationRepository(BaseRepository[Invitation]):
    model = Invitation

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(Invitation).where(Invitation.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_for_email(self, workspace_id: UUID, email: str) -> Invitation | None:
        """Нет отдельного статуса-колонки (см. model.py) — "pending" здесь
        значит `accepted_at IS NULL AND expires_at > now()`, вычисляется тем
        же способом, что и `Invitation.status`, просто на уровне SQL, а не
        Python-property (для WHERE это нужно сделать в БД, не в памяти).
        """
        stmt = select(Invitation).where(
            Invitation.workspace_id == workspace_id,
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(UTC),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
