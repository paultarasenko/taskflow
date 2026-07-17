"""FastAPI-роутер модуля `auth`.

`/auth/refresh` и `/auth/logout` — extension point (см. docstring
core/security/jwt.py и auth/schema.py:TokenResponse), не реализованы в
этом шаге: им нужно хранилище ревокации, которого пока нет.
"""

from fastapi import APIRouter, status

from app.core.dependencies import AuthServiceDep
from app.modules.auth.schema import LoginRequest, RegisterRequest, TokenResponse
from app.modules.users.schema import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, auth_service: AuthServiceDep) -> UserRead:
    user = await auth_service.register(data)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    user = await auth_service.authenticate(data.email, data.password)
    access_token = auth_service.create_access_token_for(user)
    return TokenResponse(access_token=access_token)
