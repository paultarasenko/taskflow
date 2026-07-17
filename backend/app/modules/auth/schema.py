"""Pydantic DTO модуля `auth`."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Только access_token — issuance refresh-токена и `/auth/refresh`
    с ревокацией остаются extension point (см. docstring
    core/security/jwt.py:create_refresh_token).
    """

    access_token: str
    token_type: str = "bearer"
