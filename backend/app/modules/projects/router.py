"""FastAPI-роутер модуля `projects`.

Плоские роуты (`/projects`, не `/workspaces/{id}/projects`) — сознательное
отклонение от раздела 5.4 архитектурного документа, см. обоснование в
docs/PROJECT_STATE.md (Этап 5, "Конфликт с ранее принятым API-дизайном").
`workspace_id` передаётся телом (POST) или query-параметром (GET) вместо
пути; вся repository-логика (`list_for_workspace`) не изменилась.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, ProjectServiceDep
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.projects.schema import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate, current_user: CurrentUser, project_service: ProjectServiceDep
) -> ProjectRead:
    project = await project_service.create(data, current_user)
    return ProjectRead.model_validate(project)


@router.get("", response_model=PaginatedResponse[ProjectRead])
async def list_projects(
    workspace_id: UUID,
    current_user: CurrentUser,
    project_service: ProjectServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
) -> PaginatedResponse[ProjectRead]:
    items, total = await project_service.list_for_workspace(
        workspace_id, current_user, limit=pagination.limit, offset=pagination.offset
    )
    return PaginatedResponse(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID, current_user: CurrentUser, project_service: ProjectServiceDep
) -> ProjectRead:
    project = await project_service.get_by_id(project_id, current_user)
    return ProjectRead.model_validate(project)
