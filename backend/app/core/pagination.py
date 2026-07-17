"""Единый контракт пагинации для всех list-эндпоинтов.

См. docs/01-architecture-and-design.md, раздел 5.0:
{"items": [...], "total": N, "limit": L, "offset": O}
"""

from pydantic import BaseModel, Field

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class PaginationParams(BaseModel):
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
