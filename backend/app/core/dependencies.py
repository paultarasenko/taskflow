"""Фабрики зависимостей для FastAPI `Depends()`.

Сервисы и репозитории не создают свои зависимости сами (см. ADR-0004) —
всё собирается здесь.
"""

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security.jwt import decode_token
from app.database.session import get_session
from app.modules.auth.service import AuthService
from app.modules.comments.repository import PostgresCommentRepository
from app.modules.comments.service import CommentService
from app.modules.notifications.repository import PostgresNotificationRepository
from app.modules.notifications.service import NotificationService
from app.modules.projects.repository import (
    PostgresProjectMemberRepository,
    PostgresProjectRepository,
)
from app.modules.projects.service import ProjectService
from app.modules.tasks.repository import (
    PostgresBoardRepository,
    PostgresColumnRepository,
    PostgresTaskAssigneeRepository,
    PostgresTaskRepository,
)
from app.modules.tasks.service import TaskService
from app.modules.users.model import User
from app.modules.users.repository import PostgresUserRepository
from app.modules.users.service import UserService
from app.modules.workspace.model import WorkspaceMember
from app.modules.workspace.repository import (
    PostgresInvitationRepository,
    PostgresWorkspaceMemberRepository,
    PostgresWorkspaceRepository,
)
from app.modules.workspace.service import WorkspaceService

# --- Settings ---


def settings_dependency() -> Settings:
    return get_settings()


# --- Database session ---


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


# Type alias для router-сигнатур: `session: DbSession` вместо повторения
# `Annotated[AsyncSession, Depends(get_db_session)]` в каждом эндпоинте.
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# --- Repositories ---
# Один репозиторий на запрос, через DbSession — не кэшируются между запросами
# (сессия и так живёт только на время запроса, см. database/session.py).


def get_user_repository(session: DbSession) -> PostgresUserRepository:
    return PostgresUserRepository(session)


def get_workspace_repository(session: DbSession) -> PostgresWorkspaceRepository:
    return PostgresWorkspaceRepository(session)


def get_workspace_member_repository(session: DbSession) -> PostgresWorkspaceMemberRepository:
    return PostgresWorkspaceMemberRepository(session)


def get_invitation_repository(session: DbSession) -> PostgresInvitationRepository:
    return PostgresInvitationRepository(session)


def get_project_repository(session: DbSession) -> PostgresProjectRepository:
    return PostgresProjectRepository(session)


def get_project_member_repository(session: DbSession) -> PostgresProjectMemberRepository:
    return PostgresProjectMemberRepository(session)


def get_task_repository(session: DbSession) -> PostgresTaskRepository:
    return PostgresTaskRepository(session)


def get_board_repository(session: DbSession) -> PostgresBoardRepository:
    return PostgresBoardRepository(session)


def get_column_repository(session: DbSession) -> PostgresColumnRepository:
    return PostgresColumnRepository(session)


def get_notification_repository(session: DbSession) -> PostgresNotificationRepository:
    return PostgresNotificationRepository(session)


def get_task_assignee_repository(session: DbSession) -> PostgresTaskAssigneeRepository:
    return PostgresTaskAssigneeRepository(session)


def get_comment_repository(session: DbSession) -> PostgresCommentRepository:
    return PostgresCommentRepository(session)


UserRepositoryDep = Annotated[PostgresUserRepository, Depends(get_user_repository)]
WorkspaceRepositoryDep = Annotated[PostgresWorkspaceRepository, Depends(get_workspace_repository)]
WorkspaceMemberRepositoryDep = Annotated[
    PostgresWorkspaceMemberRepository, Depends(get_workspace_member_repository)
]
InvitationRepositoryDep = Annotated[
    PostgresInvitationRepository, Depends(get_invitation_repository)
]
ProjectRepositoryDep = Annotated[PostgresProjectRepository, Depends(get_project_repository)]
ProjectMemberRepositoryDep = Annotated[
    PostgresProjectMemberRepository, Depends(get_project_member_repository)
]
TaskRepositoryDep = Annotated[PostgresTaskRepository, Depends(get_task_repository)]
BoardRepositoryDep = Annotated[PostgresBoardRepository, Depends(get_board_repository)]
ColumnRepositoryDep = Annotated[PostgresColumnRepository, Depends(get_column_repository)]
NotificationRepositoryDep = Annotated[
    PostgresNotificationRepository, Depends(get_notification_repository)
]
TaskAssigneeRepositoryDep = Annotated[
    PostgresTaskAssigneeRepository, Depends(get_task_assignee_repository)
]
CommentRepositoryDep = Annotated[PostgresCommentRepository, Depends(get_comment_repository)]


# --- Services ---


def get_auth_service(user_repository: UserRepositoryDep) -> AuthService:
    return AuthService(user_repository)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_user_service(user_repository: UserRepositoryDep) -> UserService:
    return UserService(user_repository)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_notification_service(
    notification_repository: NotificationRepositoryDep,
) -> NotificationService:
    return NotificationService(notification_repository)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


def get_comment_service(
    comment_repository: CommentRepositoryDep,
    task_repository: TaskRepositoryDep,
    project_repository: ProjectRepositoryDep,
    workspace_member_repository: WorkspaceMemberRepositoryDep,
    notification_service: NotificationServiceDep,
) -> CommentService:
    return CommentService(
        comment_repository,
        task_repository,
        project_repository,
        workspace_member_repository,
        notification_service,
    )


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


def get_workspace_service(
    workspace_repository: WorkspaceRepositoryDep,
    member_repository: WorkspaceMemberRepositoryDep,
    user_repository: UserRepositoryDep,
    invitation_repository: InvitationRepositoryDep,
) -> WorkspaceService:
    return WorkspaceService(
        workspace_repository, member_repository, user_repository, invitation_repository
    )


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_task_service(
    task_repository: TaskRepositoryDep,
    board_repository: BoardRepositoryDep,
    column_repository: ColumnRepositoryDep,
    project_repository: ProjectRepositoryDep,
    workspace_member_repository: WorkspaceMemberRepositoryDep,
    assignee_repository: TaskAssigneeRepositoryDep,
    notification_service: NotificationServiceDep,
) -> TaskService:
    return TaskService(
        task_repository,
        board_repository,
        column_repository,
        project_repository,
        workspace_member_repository,
        assignee_repository,
        notification_service,
    )


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_project_service(
    project_repository: ProjectRepositoryDep,
    workspace_member_repository: WorkspaceMemberRepositoryDep,
    task_service: TaskServiceDep,
) -> ProjectService:
    return ProjectService(project_repository, workspace_member_repository, task_service)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


# --- Current user (JWT) ---
# HTTPBearer, а не OAuth2PasswordBearer: API принимает JSON, а не
# form-encoded username/password (см. POST /auth/login) — HTTPBearer даёт
# в Swagger UI простую кнопку "Authorize" с полем для вставки токена,
# без притворства, что здесь полноценный OAuth2-флоу.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    user_repository: UserRepositoryDep,
) -> User:
    if credentials is None:
        raise UnauthorizedError("Требуется авторизация")

    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Токен не содержит идентификатора пользователя")

    user = await user_repository.get_by_id(UUID(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("Пользователь не найден или деактивирован")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# --- Workspace membership (RBAC foundation) ---
# Путевой параметр `workspace_id` подхватывается FastAPI автоматически —
# работает как Depends() на роутах вида `/workspaces/{workspace_id}`.
# Для эндпоинтов, где workspace_id приходит из тела запроса (POST /projects,
# POST /tasks — см. раздел о конфликте роутов в PROJECT_STATE.md), тот же
# репозиторный вызов делается явно внутри сервиса, не через эту функцию.


async def require_workspace_member(
    workspace_id: UUID,
    current_user: CurrentUser,
    workspace_member_repository: WorkspaceMemberRepositoryDep,
) -> WorkspaceMember:
    membership = await workspace_member_repository.get_membership(workspace_id, current_user.id)
    if membership is None:
        raise PermissionDeniedError("Вы не участник этого workspace")
    return membership


CurrentWorkspaceMembership = Annotated[WorkspaceMember, Depends(require_workspace_member)]
