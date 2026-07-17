"""Единая точка регистрации всех моделей в SQLAlchemy registry.

Зачем: relationship-таргеты объявлены строками (`Mapped[list["Comment"]]`),
и SQLAlchemy резолвит их лениво, при первой конфигурации mapper'ов — против
registry классов, УЖЕ импортированных в рантайме процесса. Любой отдельный
entry point (Alembic, seed-скрипт, тесты), который не импортировал модуль с
нужным классом напрямую, падает с `InvalidRequestError: failed to locate a
name (...)` — поймано реальным прогоном (см. историю коммитов Этапа 4).

Вместо того чтобы держать один и тот же список импортов в alembic/env.py,
scripts/seed.py и tests/conftest.py (и забыть его обновить при следующем
модуле), это делается один раз здесь; остальные места импортируют только
этот модуль.
"""

from app.modules.ai.model import AIRequest
from app.modules.comments.model import Comment
from app.modules.notifications.model import Notification
from app.modules.projects.model import Project, ProjectMember
from app.modules.tasks.model import (
    ActivityLog,
    Board,
    Column,
    Tag,
    Task,
    TaskAssignee,
    TaskTag,
)
from app.modules.users.model import User
from app.modules.workspace.model import Invitation, Workspace, WorkspaceMember

__all__ = [
    "AIRequest",
    "ActivityLog",
    "Board",
    "Column",
    "Comment",
    "Invitation",
    "Notification",
    "Project",
    "ProjectMember",
    "Tag",
    "Task",
    "TaskAssignee",
    "TaskTag",
    "User",
    "Workspace",
    "WorkspaceMember",
]
