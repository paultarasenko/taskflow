"""Repository integration tests для `tasks`: создание доски/колонки/задачи,
фильтрация `list_by_project` по статусу — тот же контракт, что у
`GET /projects/{id}/tasks?status=` (раздел 5.5 архитектурного документа).
"""

from app.core.security.password import hash_password
from app.modules.projects.model import Project
from app.modules.tasks.entity import TaskPriority, TaskStatus
from app.modules.tasks.model import Board, Column, Task
from app.modules.tasks.repository import PostgresTaskRepository
from app.modules.users.model import User
from app.modules.workspace.model import Workspace
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_project_with_column(db_session: AsyncSession) -> tuple[Project, Column, User]:
    user = User(email="pm@example.com", hashed_password=hash_password("x"), full_name="PM")
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(name="Acme", slug="acme-tasks", owner_id=user.id)
    db_session.add(workspace)
    await db_session.flush()

    project = Project(workspace_id=workspace.id, name="Backend")
    db_session.add(project)
    await db_session.flush()

    board = Board(project_id=project.id, name="Board")
    db_session.add(board)
    await db_session.flush()

    column = Column(board_id=board.id, name="Todo", position=0)
    db_session.add(column)
    await db_session.flush()

    return project, column, user


async def test_list_by_project_filters_by_status(db_session: AsyncSession) -> None:
    project, column, user = await _make_project_with_column(db_session)
    repo = PostgresTaskRepository(db_session)

    await repo.add(
        Task(
            column_id=column.id,
            project_id=project.id,
            title="Todo task",
            author_id=user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )
    )
    await repo.add(
        Task(
            column_id=column.id,
            project_id=project.id,
            title="Done task",
            author_id=user.id,
            status=TaskStatus.DONE,
            priority=TaskPriority.LOW,
        )
    )

    todo_items, todo_total = await repo.list_by_project(
        project.id, limit=50, offset=0, status=TaskStatus.TODO
    )
    all_items, all_total = await repo.list_by_project(project.id, limit=50, offset=0)

    assert todo_total == 1
    assert [t.title for t in todo_items] == ["Todo task"]
    assert all_total == 2


async def test_soft_deleted_task_excluded_from_list(db_session: AsyncSession) -> None:
    project, column, user = await _make_project_with_column(db_session)
    repo = PostgresTaskRepository(db_session)

    task = await repo.add(
        Task(
            column_id=column.id,
            project_id=project.id,
            title="To be deleted",
            author_id=user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )
    )
    await repo.delete(task)

    items, total = await repo.list_by_project(project.id, limit=50, offset=0)
    assert total == 0
    assert list(items) == []
