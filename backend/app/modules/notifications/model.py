"""SQLAlchemy-модель Notification."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.tasks.model import Task
    from app.modules.users.model import User


class NotificationType(enum.StrEnum):
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    COMMENT = "comment"
    MENTIONED = "mentioned"


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False
    )
    related_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    user: Mapped["User"] = relationship()
    related_task: Mapped["Task | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type} is_read={self.is_read}>"
