"""FastAPI-роутер модуля `users`."""

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, UserServiceDep
from app.modules.users.schema import PasswordChange, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_current_user_profile(
    data: UserUpdate, current_user: CurrentUser, user_service: UserServiceDep
) -> UserRead:
    user = await user_service.update_profile(current_user, data)
    return UserRead.model_validate(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_current_user_password(
    data: PasswordChange, current_user: CurrentUser, user_service: UserServiceDep
) -> None:
    await user_service.change_password(current_user, data)
