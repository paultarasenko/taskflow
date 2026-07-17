"""Repository для модуля `projects`."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select

from app.database.repository import BaseRepository
from app.modules.projects.model import Project, ProjectMember


class ProjectRepository(Protocol):
    async def get_by_id(self, id_: UUID) -> Project | None: ...
    async def list_for_workspace(
        self, workspace_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Project], int]: ...
    async def add(self, instance: Project) -> Project: ...


class PostgresProjectRepository(BaseRepository[Project]):
    model = Project

    async def list_for_workspace(
        self, workspace_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Project], int]:
        stmt = self._base_query().where(Project.workspace_id == workspace_id)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Project.created_at).limit(limit).offset(offset)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total


class PostgresProjectMemberRepository(BaseRepository[ProjectMember]):
    model = ProjectMember

    async def get_membership(self, project_id: UUID, user_id: UUID) -> ProjectMember | None:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
