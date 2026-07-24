"""Бизнес-логика модуля `tasks`."""

import logging
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationAppError,
)
from app.modules.notifications.service import NotificationService
from app.modules.projects.repository import PostgresProjectRepository
from app.modules.tasks.entity import ALLOWED_TRANSITIONS, TaskPriority, TaskStatus
from app.modules.tasks.model import Board, Column, Task, TaskAssignee
from app.modules.tasks.repository import (
    PostgresBoardRepository,
    PostgresColumnRepository,
    PostgresTaskAssigneeRepository,
    PostgresTaskRepository,
)
from app.modules.tasks.schema import TaskCreate, TaskRead, TaskUpdate
from app.modules.users.model import User
from app.modules.websocket.connection_manager import ConnectionManager
from app.modules.websocket.schema import WSEvent, WSEventType
from app.modules.workspace.repository import PostgresWorkspaceMemberRepository

DEFAULT_COLUMN_NAMES = ["Ideas", "Development", "Testing", "Done"]

logger = logging.getLogger(__name__)


def _validate_status_transition(current: TaskStatus, new: TaskStatus) -> None:
    """Использует `ALLOWED_TRANSITIONS` из entity.py (ADR-0004) напрямую —
    без полного маппинга ORM<->TaskEntity, который пока не нужен нигде,
    кроме этой одной проверки. Полный маппинг остаётся extension point,
    если бизнес-правил вокруг Task наберётся больше (WIP-лимиты, права на
    move) — см. ADR-0004.
    """
    if new == current:
        return
    if new not in ALLOWED_TRANSITIONS[current]:
        raise ValidationAppError(f"Недопустимый переход статуса: {current} -> {new}")


class TaskService:
    def __init__(
        self,
        task_repository: PostgresTaskRepository,
        board_repository: PostgresBoardRepository,
        column_repository: PostgresColumnRepository,
        project_repository: PostgresProjectRepository,
        workspace_member_repository: PostgresWorkspaceMemberRepository,
        assignee_repository: PostgresTaskAssigneeRepository,
        notification_service: NotificationService,
        connection_manager: ConnectionManager,
    ) -> None:
        self._tasks = task_repository
        self._boards = board_repository
        self._columns = column_repository
        self._projects = project_repository
        self._workspace_members = workspace_member_repository
        self._assignees = assignee_repository
        self._notifications = notification_service
        self._connections = connection_manager

    async def _publish(
        self, project_id: UUID, event_type: WSEventType, payload: dict[str, Any]
    ) -> None:
        """Единая точка публикации — раздел 5.10, комната = project_id.
        Ошибка Redis не должна ронять бизнес-операцию (задача уже сохранена
        в БД к этому моменту): realtime — дополнительный канал уведомления,
        не источник истины.
        """
        event = WSEvent(type=event_type, payload=payload)
        try:
            await self._connections.publish(project_id, event.model_dump_json())
        except Exception:  # noqa: BLE001 — публикация в WS не должна ломать API-ответ
            logger.warning("Не удалось опубликовать WS-событие %s", event_type, exc_info=True)

    async def _require_project_access(self, project_id: UUID, user: User) -> None:
        """Тот же паттерн, что в ProjectService._require_workspace_membership —
        сознательно не вынесен в общий сервис/утилиту (см. Правила работы
        Этапа 5: "не усложняй раньше времени"). Если проверка понадобится
        третьему модулю, тогда и есть смысл выносить.
        """
        project = await self._projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Проект {project_id} не найден")
        membership = await self._workspace_members.get_membership(project.workspace_id, user.id)
        if membership is None:
            raise PermissionDeniedError("Вы не участник workspace этого проекта")

    async def create_default_board(self, project_id: UUID) -> Board:
        """Board 1:1 с Project (ERD) — создаётся вместе с проектом
        (ProjectService.create), не отдельным эндпоинтом: своих
        board/column-эндпоинтов в этом шаге ещё нет (Kanban UI — Этап 9), но
        без доски задачу некуда положить. Доступ уже проверен вызывающей
        стороной (ProjectService уже проверил membership перед созданием
        проекта) — здесь повторная проверка была бы избыточной.
        """
        board = await self._boards.add(Board(project_id=project_id, name="Main Board"))
        for position, name in enumerate(DEFAULT_COLUMN_NAMES):
            await self._columns.add(Column(board_id=board.id, name=name, position=position))
        return board

    async def create(self, data: TaskCreate, author: User) -> Task:
        await self._require_project_access(data.project_id, author)

        column_id = data.column_id
        if column_id is None:
            board = await self._boards.get_by_project(data.project_id)
            if board is None:
                raise NotFoundError(f"У проекта {data.project_id} нет доски")
            columns = await self._columns.list_by_board(board.id)
            if not columns:
                raise NotFoundError(f"У доски проекта {data.project_id} нет колонок")
            column_id = columns[0].id

        task = Task(
            project_id=data.project_id,
            column_id=column_id,
            title=data.title,
            description=data.description,
            author_id=author.id,
            priority=data.priority,
            due_date=data.due_date,
            status=TaskStatus.TODO,
        )
        created = await self._tasks.add(task)
        await self._publish(
            data.project_id,
            WSEventType.TASK_CREATED,
            TaskRead.model_validate(created).model_dump(mode="json"),
        )
        return created

    async def get_by_id(self, task_id: UUID, current_user: User) -> Task:
        task = await self._tasks.get_by_id(task_id)
        if task is None:
            raise NotFoundError(f"Задача {task_id} не найдена")
        await self._require_project_access(task.project_id, current_user)
        return task

    async def list_by_project(
        self,
        project_id: UUID,
        current_user: User,
        limit: int,
        offset: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
    ) -> tuple[Sequence[Task], int]:
        await self._require_project_access(project_id, current_user)
        return await self._tasks.list_by_project(
            project_id, limit=limit, offset=offset, status=status, priority=priority
        )

    async def update(self, task_id: UUID, data: TaskUpdate, current_user: User) -> Task:
        task = await self.get_by_id(task_id, current_user)

        if data.status is not None:
            _validate_status_transition(task.status, data.status)
            task.status = data.status
        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
        if data.priority is not None:
            task.priority = data.priority
        if data.due_date is not None:
            task.due_date = data.due_date
        is_move = data.column_id is not None
        if data.column_id is not None:
            task.column_id = data.column_id

        saved = await self._tasks.save(task)
        event_type = WSEventType.TASK_MOVED if is_move else WSEventType.TASK_UPDATED
        await self._publish(
            saved.project_id, event_type, TaskRead.model_validate(saved).model_dump(mode="json")
        )
        return saved

    async def delete(self, task_id: UUID, current_user: User) -> None:
        task = await self.get_by_id(task_id, current_user)
        project_id = task.project_id
        await self._tasks.delete(task)
        await self._publish(project_id, WSEventType.TASK_DELETED, {"id": str(task_id)})

    async def assign_user(
        self, task_id: UUID, assignee_user_id: UUID, current_user: User
    ) -> TaskAssignee:
        """Назначаемый должен быть участником того же workspace — иначе можно
        было бы "назначить" задачу человеку, у которого в принципе нет
        доступа посмотреть проект. Уведомление создаётся здесь же, а не
        отдельным вызовом снаружи: назначение без уведомления — незавершённая
        операция с точки зрения пользователя.
        """
        task = await self.get_by_id(task_id, current_user)

        # get_by_id уже гарантировал, что проект существует (через
        # _require_project_access) — второй fetch здесь ради workspace_id,
        # не ради проверки на None.
        project = await self._projects.get_by_id(task.project_id)
        assert project is not None  # noqa: S101 — инвариант, не пользовательский ввод

        assignee_membership = await self._workspace_members.get_membership(
            project.workspace_id, assignee_user_id
        )
        if assignee_membership is None:
            raise PermissionDeniedError(
                "Нельзя назначить задачу пользователю, не состоящему в workspace проекта"
            )

        if await self._assignees.exists(task_id, assignee_user_id):
            raise ConflictError("Пользователь уже назначен на эту задачу")

        assignment = await self._assignees.add(
            TaskAssignee(task_id=task_id, user_id=assignee_user_id)
        )
        await self._notifications.notify_task_assigned(assignee_user_id, task_id)
        await self._publish(
            task.project_id,
            WSEventType.NOTIFICATION_CREATED,
            {"user_id": str(assignee_user_id), "type": "assigned", "related_task_id": str(task_id)},
        )
        return assignment
