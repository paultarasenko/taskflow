"""Бизнес-логика модуля `projects`."""

from collections.abc import Sequence
from uuid import UUID

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.modules.projects.model import Project
from app.modules.projects.repository import PostgresProjectRepository
from app.modules.projects.schema import ProjectCreate
from app.modules.tasks.service import TaskService
from app.modules.users.model import User
from app.modules.workspace.repository import PostgresWorkspaceMemberRepository


class ProjectService:
    def __init__(
        self,
        project_repository: PostgresProjectRepository,
        workspace_member_repository: PostgresWorkspaceMemberRepository,
        task_service: TaskService,
    ) -> None:
        self._projects = project_repository
        self._workspace_members = workspace_member_repository
        # Кросс-модульная зависимость через сервис, не через чужой репозиторий
        # напрямую (раздел 3.1) — Board/Column принадлежат модулю `tasks`.
        self._task_service = task_service

    async def _require_workspace_membership(self, workspace_id: UUID, user: User) -> None:
        membership = await self._workspace_members.get_membership(workspace_id, user.id)
        if membership is None:
            raise PermissionDeniedError("Вы не участник этого workspace")

    async def create(self, data: ProjectCreate, current_user: User) -> Project:
        await self._require_workspace_membership(data.workspace_id, current_user)

        project = await self._projects.add(
            Project(
                workspace_id=data.workspace_id,
                name=data.name,
                description=data.description,
            )
        )
        await self._task_service.create_default_board(project.id)
        return project

    async def list_for_workspace(
        self, workspace_id: UUID, current_user: User, limit: int, offset: int
    ) -> tuple[Sequence[Project], int]:
        await self._require_workspace_membership(workspace_id, current_user)
        return await self._projects.list_for_workspace(workspace_id, limit=limit, offset=offset)

    async def get_by_id(self, project_id: UUID, current_user: User) -> Project:
        project = await self._projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Проект {project_id} не найден")
        await self._require_workspace_membership(project.workspace_id, current_user)
        return project
