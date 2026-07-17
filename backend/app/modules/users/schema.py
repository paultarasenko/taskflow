"""Pydantic DTO модуля `users`."""

from pydantic import BaseModel, Field

from app.shared.schemas import IDMixin, ORMModel, TimestampMixin


class UserRead(ORMModel, IDMixin, TimestampMixin):
    """Публичная схема пользователя — hashed_password сюда никогда не попадает
    (поле просто не объявлено), а не вычищается постфактум.
    """

    email: str
    full_name: str
    avatar_url: str | None
    is_active: bool


class UserUpdate(BaseModel):
    """Все поля опциональны — PATCH: обновляются только переданные.
    Email осознанно не редактируется здесь — смена email требует
    подтверждения (Roadmap), иначе можно тихо угнать чужой аккаунт,
    просто зная текущий пароль.
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_url: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
