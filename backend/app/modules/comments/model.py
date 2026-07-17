"""SQLAlchemy-модель Comment."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.tasks.model import Task
    from app.modules.users.model import User


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`edited_at` — отдельное поле, не UpdatedAtMixin: ERD различает
    "когда создан" и "когда отредактирован" явно, и edited_at nullable
    (пока комментарий не редактировали — он None), в отличие от обычного
    updated_at, который обычно выставляется сразу при создании.
    """

    __tablename__ = "comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped["Task"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<Comment id={self.id} task_id={self.task_id}>"
