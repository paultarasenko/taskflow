"""Бизнес-логика модуля `comments`."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security.permissions import WorkspaceRole, require_workspace_role
from app.modules.comments.model import Comment
from app.modules.comments.repository import PostgresCommentRepository
from app.modules.comments.schema import CommentCreate, CommentUpdate
from app.modules.notifications.service import NotificationService
from app.modules.projects.repository import PostgresProjectRepository
from app.modules.tasks.repository import PostgresTaskRepository
from app.modules.users.model import User
from app.modules.workspace.repository import PostgresWorkspaceMemberRepository


class CommentService:
    """`_require_project_access` — третье по счёту дублирование одного и
    того же паттерна (после `TaskService`, `ProjectService`). Осознанно не
    вынесено в общую утилиту в рамках этого этапа — рефакторинг уже
    протестированных `TaskService`/`ProjectService` без явного запроса на
    это не входил в задачу Этапа 7 (см. docs/PROJECT_STATE.md). Кандидат на
    отдельный этап технического долга.
    """

    def __init__(
        self,
        comment_repository: PostgresCommentRepository,
        task_repository: PostgresTaskRepository,
        project_repository: PostgresProjectRepository,
        workspace_member_repository: PostgresWorkspaceMemberRepository,
        notification_service: NotificationService,
    ) -> None:
        self._comments = comment_repository
        self._tasks = task_repository
        self._projects = project_repository
        self._workspace_members = workspace_member_repository
        self._notifications = notification_service

    async def _require_project_access(self, project_id: UUID, user: User) -> WorkspaceRole:
        project = await self._projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Проект {project_id} не найден")
        membership = await self._workspace_members.get_membership(project.workspace_id, user.id)
        if membership is None:
            raise PermissionDeniedError("Вы не участник workspace этого проекта")
        return membership.role

    async def create(self, task_id: UUID, data: CommentCreate, author: User) -> Comment:
        task = await self._tasks.get_by_id(task_id)
        if task is None:
            raise NotFoundError(f"Задача {task_id} не найдена")
        await self._require_project_access(task.project_id, author)

        comment = await self._comments.add(
            Comment(task_id=task_id, author_id=author.id, content=data.content)
        )

        # Не уведомляем автора задачи о его же комментарии.
        if task.author_id != author.id:
            await self._notifications.notify_new_comment(task.author_id, task_id)

        return comment

    async def list_by_task(
        self, task_id: UUID, current_user: User, limit: int, offset: int
    ) -> tuple[Sequence[Comment], int]:
        task = await self._tasks.get_by_id(task_id)
        if task is None:
            raise NotFoundError(f"Задача {task_id} не найдена")
        await self._require_project_access(task.project_id, current_user)
        return await self._comments.list_by_task(task_id, limit=limit, offset=offset)

    async def _get_with_access_check(
        self, comment_id: UUID, user: User
    ) -> tuple[Comment, WorkspaceRole]:
        comment = await self._comments.get_by_id(comment_id)
        if comment is None:
            raise NotFoundError(f"Комментарий {comment_id} не найден")
        task = await self._tasks.get_by_id(comment.task_id)
        if task is None:  # pragma: no cover — task всегда есть, FK-гарантия
            raise NotFoundError(f"Задача {comment.task_id} не найдена")
        role = await self._require_project_access(task.project_id, user)
        return comment, role

    @staticmethod
    def _require_author_or_admin(comment: Comment, user: User, role: WorkspaceRole) -> None:
        if comment.author_id == user.id:
            return
        if require_workspace_role(role, WorkspaceRole.ADMIN):
            return
        raise PermissionDeniedError("Редактировать/удалять можно только свои комментарии")

    async def update(self, comment_id: UUID, data: CommentUpdate, current_user: User) -> Comment:
        comment, role = await self._get_with_access_check(comment_id, current_user)
        self._require_author_or_admin(comment, current_user, role)

        comment.content = data.content
        comment.edited_at = datetime.now(UTC)
        return await self._comments.save(comment)

    async def delete(self, comment_id: UUID, current_user: User) -> None:
        comment, role = await self._get_with_access_check(comment_id, current_user)
        self._require_author_or_admin(comment, current_user, role)
        await self._comments.delete(comment)
