"""SQLAlchemy-модель AIRequest."""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.projects.model import Project
    from app.modules.users.model import User


class AIRequestKind(enum.StrEnum):
    TASK_FROM_TEXT = "task_from_text"
    SUBTASKS = "subtasks"
    SUMMARY = "summary"
    PRIORITIZE = "prioritize"


class AIRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`provider` — свободная строка, не Enum: единственная реализация в MVP —
    "openai" (см. ADR-0005), но colonка не должна требовать миграции при
    добавлении Anthropic/Gemini/OpenRouter — тогда это просто новое значение.
    """

    __tablename__ = "ai_requests"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[AIRequestKind] = mapped_column(
        Enum(AIRequestKind, name="ai_request_kind"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="openai")
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    project: Mapped["Project"] = relationship()
    requester: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<AIRequest id={self.id} kind={self.kind} provider={self.provider!r}>"
