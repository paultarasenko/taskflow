"""SQLAlchemy declarative base.

Все модели модулей (app/modules/*/model.py) наследуются от этого Base.
Реальные модели и Alembic-миграции — Этап 4.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
