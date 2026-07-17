"""FastAPI-роутер модуля `workspace`.

Два router-объекта: `router` (всё под `/workspaces`, требует auth) и
`invitation_router` (`/invitations/{token}` — публичный GET для проверки
статуса ещё незарегистрированным человеком, POST .../accept требует auth).
main.py подключает оба.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, CurrentWorkspaceMembership, WorkspaceServiceDep
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.workspace.schema import (
    InvitationCreate,
    InvitationPublicRead,
    InvitationRead,
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceMemberRoleUpdate,
    WorkspaceRead,
)

router = APIRouter(prefix="/workspaces", tags=["workspace"])
invitation_router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate, current_user: CurrentUser, workspace_service: WorkspaceServiceDep
) -> WorkspaceRead:
    workspace = await workspace_service.create(data.name, current_user)
    return WorkspaceRead.model_validate(workspace)


@router.get("", response_model=PaginatedResponse[WorkspaceRead])
async def list_my_workspaces(
    current_user: CurrentUser,
    workspace_service: WorkspaceServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
) -> PaginatedResponse[WorkspaceRead]:
    items, total = await workspace_service.list_for_user(
        current_user, limit=pagination.limit, offset=pagination.offset
    )
    return PaginatedResponse(
        items=[WorkspaceRead.model_validate(w) for w in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: UUID,
    workspace_service: WorkspaceServiceDep,
    # Само наличие этого Depends — уже проверка доступа (404/403 до вызова
    # сервиса, если не участник); возвращаемое значение здесь не нужно.
    _membership: CurrentWorkspaceMembership,
) -> WorkspaceRead:
    workspace = await workspace_service.get_by_id(workspace_id)
    return WorkspaceRead.model_validate(workspace)


# --- Members ---


@router.get("/{workspace_id}/members", response_model=PaginatedResponse[WorkspaceMemberRead])
async def list_workspace_members(
    workspace_id: UUID,
    workspace_service: WorkspaceServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    _membership: CurrentWorkspaceMembership,
) -> PaginatedResponse[WorkspaceMemberRead]:
    items, total = await workspace_service.list_members(
        workspace_id, limit=pagination.limit, offset=pagination.offset
    )
    return PaginatedResponse(
        items=[WorkspaceMemberRead.model_validate(m) for m in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace_id: UUID,
    data: WorkspaceMemberAdd,
    workspace_service: WorkspaceServiceDep,
    membership: CurrentWorkspaceMembership,
) -> WorkspaceMemberRead:
    new_member = await workspace_service.add_member(workspace_id, data, membership.role)
    return WorkspaceMemberRead.model_validate(new_member)


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberRead)
async def change_workspace_member_role(
    workspace_id: UUID,
    user_id: UUID,
    data: WorkspaceMemberRoleUpdate,
    workspace_service: WorkspaceServiceDep,
    membership: CurrentWorkspaceMembership,
) -> WorkspaceMemberRead:
    updated = await workspace_service.change_member_role(
        workspace_id, user_id, data.role, membership.role
    )
    return WorkspaceMemberRead.model_validate(updated)


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    workspace_service: WorkspaceServiceDep,
    membership: CurrentWorkspaceMembership,
) -> None:
    await workspace_service.remove_member(workspace_id, user_id, current_user.id, membership.role)


# --- Invitations ---


@router.post(
    "/{workspace_id}/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    workspace_id: UUID,
    data: InvitationCreate,
    current_user: CurrentUser,
    workspace_service: WorkspaceServiceDep,
    membership: CurrentWorkspaceMembership,
) -> InvitationRead:
    """Реальная отправка email — extension point (см. docs/01-architecture-and-design.md,
    Roadmap: email-доставка требует Celery+SMTP, отложено с Этапа 1). Токен
    возвращается прямо в ответе — им пользуется тестовый/API-клиент вместо
    письма, пока email-доставки нет.
    """
    invitation = await workspace_service.create_invitation(
        workspace_id, data, current_user.id, membership.role
    )
    return InvitationRead.model_validate(invitation)


@invitation_router.get("/{token}", response_model=InvitationPublicRead)
async def get_invitation_status(
    token: str, workspace_service: WorkspaceServiceDep
) -> InvitationPublicRead:
    """Без авторизации — приглашённый ещё может быть незарегистрирован."""
    invitation, workspace = await workspace_service.get_invitation_by_token(token)
    return InvitationPublicRead(
        workspace_name=workspace.name,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
    )


@invitation_router.post("/{token}/accept", response_model=WorkspaceMemberRead)
async def accept_invitation(
    token: str, current_user: CurrentUser, workspace_service: WorkspaceServiceDep
) -> WorkspaceMemberRead:
    membership = await workspace_service.accept_invitation(token, current_user)
    return WorkspaceMemberRead.model_validate(membership)
