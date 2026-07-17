"""Общие Pydantic-примитивы, переиспользуемые модулями."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Базовая схема для Read-DTO, мапящихся из SQLAlchemy-моделей."""

    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    created_at: datetime


class IDMixin(BaseModel):
    id: UUID
