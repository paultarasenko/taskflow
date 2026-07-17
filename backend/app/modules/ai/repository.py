"""Repository для модуля `ai`."""

from typing import Protocol
from uuid import UUID

from app.database.repository import BaseRepository
from app.modules.ai.model import AIRequest


class AIRequestRepository(Protocol):
    async def get_by_id(self, id_: UUID) -> AIRequest | None: ...
    async def add(self, instance: AIRequest) -> AIRequest: ...


class PostgresAIRequestRepository(BaseRepository[AIRequest]):
    model = AIRequest
