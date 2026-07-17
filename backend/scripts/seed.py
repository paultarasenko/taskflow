"""Идемпотентный seed-скрипт: demo workspace, demo user, demo project, demo tasks.

Запуск: `make seed` (или `python -m scripts.seed` из backend/ с активным venv).

Это МЕХАНИЗМ наполнения, не финальный богатый dataseed с 45 задачами и 12
пользователями — та версия описана в docs/01-architecture-and-design.md,
9.5, и появится на Этапе 13 вместе с полноценным Public Demo. Здесь —
минимальный, но настоящий (реальные INSERT в реальную БД) прототип: 1 demo
workspace, 1 demo user, 1 demo project с доской и несколькими задачами.

Идемпотентность: проверяем по email demo-пользователя — если он уже есть,
ничего не создаём повторно (см. требование "не идемпотентно = дубли при
повторном запуске", раздел 9.5).

НЕ запускается автоматически при старте приложения (см. main.py) — только
явно через `make seed`.
"""

import asyncio

from app.core.security.password import hash_password
from app.core.security.permissions import WorkspaceRole
from app.database.models_registry import *  # noqa: F401, F403
from app.database.session import session_factory
from app.modules.projects.model import Project, ProjectVisibility
from app.modules.tasks.entity import TaskPriority, TaskStatus
from app.modules.tasks.model import Board, Column, Task
from app.modules.users.model import User
from app.modules.workspace.model import Workspace, WorkspaceMember
from sqlalchemy import select

DEMO_USER_EMAIL = "demo@taskflow.dev"
DEMO_USER_PASSWORD = "demo12345"  # только для локального seed, не для прода


async def seed() -> None:
    async with session_factory() as session:
        existing = await session.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        if existing.scalar_one_or_none() is not None:
            print(f"Seed уже применён — пользователь {DEMO_USER_EMAIL} существует. Пропускаю.")
            return

        # --- Demo user ---
        user = User(
            email=DEMO_USER_EMAIL,
            hashed_password=hash_password(DEMO_USER_PASSWORD),
            full_name="Demo User",
            is_active=True,
        )
        session.add(user)
        await session.flush()  # получить user.id

        # --- Demo workspace ---
        workspace = Workspace(name="Demo Company", slug="demo-company", owner_id=user.id)
        session.add(workspace)
        await session.flush()

        session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER)
        )

        # --- Demo project (public_demo — попадает в Public Demo без авторизации, Roadmap) ---
        project = Project(
            workspace_id=workspace.id,
            name="Backend",
            description="Демонстрационный проект — API и бизнес-логика TaskFlow",
            visibility=ProjectVisibility.PUBLIC_DEMO,
        )
        session.add(project)
        await session.flush()

        # --- Board + колонки (пример из ТЗ: Ideas → Development → Testing → Done) ---
        board = Board(project_id=project.id, name="Backend Board")
        session.add(board)
        await session.flush()

        column_names = ["Ideas", "Development", "Testing", "Done"]
        columns = []
        for i, name in enumerate(column_names):
            column = Column(board_id=board.id, name=name, position=i)
            session.add(column)
            columns.append(column)
        await session.flush()

        # --- Demo tasks — распределены по колонкам, не всё в Done ---
        demo_tasks = [
            ("Спроектировать схему БД", TaskStatus.DONE, TaskPriority.HIGH, 3),
            ("Настроить Alembic-миграции", TaskStatus.DONE, TaskPriority.HIGH, 3),
            ("Реализовать auth endpoints", TaskStatus.IN_PROGRESS, TaskPriority.URGENT, 1),
            ("Написать repository-тесты", TaskStatus.IN_PROGRESS, TaskPriority.MEDIUM, 1),
            ("Добавить WebSocket realtime", TaskStatus.TODO, TaskPriority.MEDIUM, 0),
            ("Подключить AI-провайдера", TaskStatus.TODO, TaskPriority.LOW, 0),
            ("Ревью security-чек-листа", TaskStatus.REVIEW, TaskPriority.HIGH, 2),
        ]
        column_by_status = {
            TaskStatus.TODO: columns[0],
            TaskStatus.IN_PROGRESS: columns[1],
            TaskStatus.REVIEW: columns[2],
            TaskStatus.DONE: columns[3],
        }
        for title, status, priority, position in demo_tasks:
            session.add(
                Task(
                    column_id=column_by_status[status].id,
                    project_id=project.id,
                    title=title,
                    author_id=user.id,
                    status=status,
                    priority=priority,
                    position=position,
                )
            )

        await session.commit()
        print("Seed применён:")
        print(f"  workspace: {workspace.slug} ({workspace.id})")
        print(f"  user:      {user.email} / пароль: {DEMO_USER_PASSWORD}")
        print(f"  project:   {project.name} ({project.id})")
        print(f"  tasks:     {len(demo_tasks)}")


if __name__ == "__main__":
    asyncio.run(seed())
