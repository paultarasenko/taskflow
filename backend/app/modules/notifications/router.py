"""FastAPI-роутер модуля `notifications`."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, NotificationServiceDep
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.notifications.schema import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedResponse[NotificationRead])
async def list_my_notifications(
    current_user: CurrentUser,
    notification_service: NotificationServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
) -> PaginatedResponse[NotificationRead]:
    items, total = await notification_service.list_for_user(
        current_user, limit=pagination.limit, offset=pagination.offset
    )
    return PaginatedResponse(
        items=[NotificationRead.model_validate(n) for n in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_as_read(
    notification_id: UUID, current_user: CurrentUser, notification_service: NotificationServiceDep
) -> NotificationRead:
    notification = await notification_service.mark_as_read(notification_id, current_user)
    return NotificationRead.model_validate(notification)
