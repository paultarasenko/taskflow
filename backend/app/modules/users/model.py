"""SQLAlchemy-модель User.

Единая таблица для профиля и auth-данных (см. ERD, docs/01-architecture-and-design.md,
раздел 4). Модуль `auth` не владеет отдельной моделью — его сервис работает
с UserRepository отсюда (см. app/modules/auth/model.py).
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.projects.model import ProjectMember
    from app.modules.workspace.model import WorkspaceMember


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Обратные связи ограничены тем, что реально нужно для RBAC-проверок.
    # Задачи/комментарии/уведомления пользователя достаются через
    # соответствующий репозиторий с фильтром по user_id, а не через ORM-граф
    # от User — иначе легко словить случайный N+1 при каждой загрузке юзера.
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
