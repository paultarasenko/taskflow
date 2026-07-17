"""Бизнес-логика модуля `auth`.

Зависит от `UserRepository` (модуль `users`), не заводит собственную модель —
см. app/modules/auth/model.py и раздел 3.1 архитектурного документа
("межмодульные границы через интерфейсы сервисов/репозиториев").
"""

from datetime import timedelta

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security.jwt import create_access_token
from app.core.security.password import hash_password, verify_password
from app.modules.auth.schema import RegisterRequest
from app.modules.users.model import User
from app.modules.users.repository import PostgresUserRepository


class AuthService:
    def __init__(self, user_repository: PostgresUserRepository) -> None:
        self._users = user_repository

    async def register(self, data: RegisterRequest) -> User:
        existing = await self._users.get_by_email(data.email)
        if existing is not None:
            raise ConflictError(f"Пользователь с email {data.email!r} уже существует")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )
        return await self._users.add(user)

    async def authenticate(self, email: str, password: str) -> User:
        """Единое сообщение об ошибке для "нет такого email" и "неверный
        пароль" — стандартная практика, чтобы не давать атакующему
        подтверждение существования конкретного email через разные ответы.
        """
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Неверный email или пароль")
        if not user.is_active:
            raise UnauthorizedError("Аккаунт деактивирован")
        return user

    def create_access_token_for(self, user: User) -> str:
        settings = get_settings()
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        return create_access_token(subject=str(user.id), expires_delta=expires_delta)
