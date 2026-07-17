"""FastAPI-роутер модуля `tasks`.

Плоские роуты (`/tasks`, не `/projects/{id}/tasks`) — то же сознательное
отклонение от раздела 5.5, что и в `projects/router.py`, см.
docs/PROJECT_STATE.md (Этап 5). Фильтры status/priority и pagination — тот
же контракт, что был бы у `GET /projects/{id}/tasks?status=&priority=`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, TaskServiceDep
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.tasks.entity import TaskPriority, TaskStatus
from app.modules.tasks.schema import (
    TaskAssigneeCreate,
    TaskAssigneeRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate, current_user: CurrentUser, task_service: TaskServiceDep
) -> TaskRead:
    task = await task_service.create(data, current_user)
    return TaskRead.model_validate(task)


@router.get("", response_model=PaginatedResponse[TaskRead])
async def list_tasks(
    project_id: UUID,
    current_user: CurrentUser,
    task_service: TaskServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> PaginatedResponse[TaskRead]:
    items, total = await task_service.list_by_project(
        project_id,
        current_user,
        limit=pagination.limit,
        offset=pagination.offset,
        status=status_filter,
        priority=priority,
    )
    return PaginatedResponse(
        items=[TaskRead.model_validate(t) for t in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID, current_user: CurrentUser, task_service: TaskServiceDep
) -> TaskRead:
    task = await task_service.get_by_id(task_id, current_user)
    return TaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID, data: TaskUpdate, current_user: CurrentUser, task_service: TaskServiceDep
) -> TaskRead:
    task = await task_service.update(task_id, data, current_user)
    return TaskRead.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID, current_user: CurrentUser, task_service: TaskServiceDep
) -> None:
    await task_service.delete(task_id, current_user)


@router.post(
    "/{task_id}/assignees", response_model=TaskAssigneeRead, status_code=status.HTTP_201_CREATED
)
async def assign_task(
    task_id: UUID, data: TaskAssigneeCreate, current_user: CurrentUser, task_service: TaskServiceDep
) -> TaskAssigneeRead:
    assignment = await task_service.assign_user(task_id, data.user_id, current_user)
    return TaskAssigneeRead.model_validate(assignment)
