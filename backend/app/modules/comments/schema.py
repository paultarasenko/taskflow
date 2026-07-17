"""Pydantic DTO модуля `comments`."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas import IDMixin, ORMModel, TimestampMixin


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class CommentRead(ORMModel, IDMixin, TimestampMixin):
    task_id: UUID
    author_id: UUID
    content: str
    edited_at: datetime | None
