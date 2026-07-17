"""Pydantic DTO модуля `projects`."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.projects.model import ProjectVisibility
from app.shared.schemas import IDMixin, ORMModel, TimestampMixin


class ProjectCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectRead(ORMModel, IDMixin, TimestampMixin):
    workspace_id: UUID
    name: str
    description: str | None
    visibility: ProjectVisibility
