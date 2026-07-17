"""Бизнес-логика модуля `users` (Service Layer)."""

from app.core.exceptions import UnauthorizedError
from app.core.security.password import hash_password, verify_password
from app.modules.users.model import User
from app.modules.users.repository import PostgresUserRepository
from app.modules.users.schema import PasswordChange, UserUpdate


class UserService:
    def __init__(self, user_repository: PostgresUserRepository) -> None:
        self._users = user_repository

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url
        return await self._users.save(user)

    async def change_password(self, user: User, data: PasswordChange) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise UnauthorizedError("Текущий пароль неверен")
        user.hashed_password = hash_password(data.new_password)
        await self._users.save(user)
