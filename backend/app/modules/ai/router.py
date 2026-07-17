"""FastAPI-роутер модуля `ai`.

Контракт эндпоинтов зафиксирован в docs/01-architecture-and-design.md,
раздел 5. Реализация — Этап 10.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/ai", tags=["ai"])

# Эндпоинты появятся на Этапе 10.
