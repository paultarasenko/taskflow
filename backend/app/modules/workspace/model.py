"""SQLAlchemy-модели Workspace, WorkspaceMember, Invitation.

`Invitation` — новая сущность, не было в ERD Этапа 1 (docs/01-architecture-and-design.md,
раздел 4): исходный API-дизайн предполагал `POST /workspaces/{id}/invite`
как разовое немедленное добавление участника по email. Токен-based flow
приглашений с раздельными create/accept/status — расширение из Этапа 6,
описано в ADR-0007.
"""

import enum
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security.permissions import WorkspaceRole
from app.database.base import Base
from app.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.projects.model import Project
    from app.modules.users.model import User

INVITATION_EXPIRY_DAYS = 7


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="workspace")

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} slug={self.slug!r}>"


class WorkspaceMember(UUIDPrimaryKeyMixin, Base):
    """Без TimestampMixin: ERD называет это поле `joined_at`, а не generic
    `created_at` — семантика важна (когда человек присоединился к workspace),
    поэтому колонка объявлена явно, а не через общий миксин.
    """

    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role"), nullable=False, default=WorkspaceRole.MEMBER
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="workspace_memberships")

    def __repr__(self) -> str:
        return f"<WorkspaceMember workspace_id={self.workspace_id} user_id={self.user_id} role={self.role}>"


class InvitationStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


class Invitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Статус — НЕ хранимая колонка, а вычисляемое свойство (`status`
    ниже): pending/accepted/expired полностью выводятся из `accepted_at` и
    `expires_at`. Нет отдельного enum-поля, которое надо было бы держать в
    синхроне фоновой job'ой ("протухла — проставить expired") — статус
    всегда корректен на момент чтения, без лишнего движущегося состояния.
    См. ADR-0007.
    """

    __tablename__ = "invitations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="invitation_role"), nullable=False, default=WorkspaceRole.MEMBER
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped["Workspace"] = relationship()
    inviter: Mapped["User"] = relationship(foreign_keys=[invited_by])

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def default_expiry() -> datetime:
        return datetime.now(UTC) + timedelta(days=INVITATION_EXPIRY_DAYS)

    @property
    def status(self) -> InvitationStatus:
        if self.accepted_at is not None:
            return InvitationStatus.ACCEPTED
        if self.expires_at < datetime.now(UTC):
            return InvitationStatus.EXPIRED
        return InvitationStatus.PENDING

    def __repr__(self) -> str:
        return f"<Invitation id={self.id} email={self.email!r} status={self.status}>"
