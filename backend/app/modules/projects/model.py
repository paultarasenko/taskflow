"""SQLAlchemy-модели Project, ProjectMember."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security.permissions import ProjectRole
from app.database.base import Base
from app.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.tasks.model import Board
    from app.modules.users.model import User
    from app.modules.workspace.model import Workspace


class ProjectVisibility(enum.StrEnum):
    PRIVATE = "private"
    WORKSPACE = "workspace"
    PUBLIC_DEMO = "public_demo"


class Project(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "projects"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[ProjectVisibility] = mapped_column(
        Enum(ProjectVisibility, name="project_visibility"),
        nullable=False,
        default=ProjectVisibility.WORKSPACE,
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="projects")
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    # Board — 1:1 в ERD (`PROJECTS ||--|| BOARDS`), но связь объявлена как
    # list на уровне ORM: SQLAlchemy 1:1 через uselist=False технически проще
    # напрямую в Board.project (см. tasks/model.py), здесь достаточно
    # обратного доступа для repository-запросов.
    board: Mapped["Board | None"] = relationship(back_populates="project", uselist=False)

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


class ProjectMember(UUIDPrimaryKeyMixin, Base):
    """Без временных полей — ERD не заводит их для PROJECT_MEMBERS (см.
    docs/01-architecture-and-design.md, раздел 4.1). Можно добавить `joined_at`
    отдельной миграцией позже, если понадобится — не меняю согласованную схему
    по своей инициативе.
    """

    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, name="project_role"), nullable=False, default=ProjectRole.EDITOR
    )

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="project_memberships")

    def __repr__(self) -> str:
        return (
            f"<ProjectMember project_id={self.project_id} user_id={self.user_id} role={self.role}>"
        )
