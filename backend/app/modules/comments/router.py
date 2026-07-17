"""FastAPI-роутер модуля `comments`.

Без общего `prefix` у APIRouter: контракт этого шага смешивает вложенный
путь (`/tasks/{task_id}/comments` — создание и список) и плоский
(`/comments/{comment_id}` — изменение и удаление). Единый префикс сюда не
ложится, поэтому каждый route задаёт полный путь сам — тот же приём, что
понадобился бы `/workspaces/{id}/invitations` + `/invitations/{token}`
(см. workspace/router.py, там решено через два router-объекта; здесь оба
пути помещаются в один модуль без разделения, т.к. это один ресурс).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CommentServiceDep, CurrentUser
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.comments.schema import CommentCreate, CommentRead, CommentUpdate

router = APIRouter(tags=["comments"])


@router.post(
    "/tasks/{task_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED
)
async def create_comment(
    task_id: UUID,
    data: CommentCreate,
    current_user: CurrentUser,
    comment_service: CommentServiceDep,
) -> CommentRead:
    comment = await comment_service.create(task_id, data, current_user)
    return CommentRead.model_validate(comment)


@router.get("/tasks/{task_id}/comments", response_model=PaginatedResponse[CommentRead])
async def list_task_comments(
    task_id: UUID,
    current_user: CurrentUser,
    comment_service: CommentServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
) -> PaginatedResponse[CommentRead]:
    items, total = await comment_service.list_by_task(
        task_id, current_user, limit=pagination.limit, offset=pagination.offset
    )
    return PaginatedResponse(
        items=[CommentRead.model_validate(c) for c in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.patch("/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: UUID,
    data: CommentUpdate,
    current_user: CurrentUser,
    comment_service: CommentServiceDep,
) -> CommentRead:
    comment = await comment_service.update(comment_id, data, current_user)
    return CommentRead.model_validate(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID, current_user: CurrentUser, comment_service: CommentServiceDep
) -> None:
    await comment_service.delete(comment_id, current_user)
