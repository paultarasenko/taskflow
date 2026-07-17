"""Доменная сущность Task — единственное отклонение от "ORM-модель = доменная модель"
в проекте (см. ADR-0004: `docs/adr/0004-module-architecture.md`).

Здесь живут правила, которые не сводятся к ORM-полям:
- допустимые переходы статуса (todo → in_progress → review → done, без прыжков через review);
- проверка WIP-лимита колонки при move;
- кто вправе переместить задачу (автор, исполнитель, admin/owner workspace).

`repository.py` мапит эту сущность в/из `model.py` (SQLAlchemy). `service.py`
работает только с этим классом, никогда напрямую с ORM-моделью.

TODO(Этап 7): полная реализация вместе с TaskService.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class TaskPriority(StrEnum):
    """Без логики переходов (в отличие от TaskStatus) — любой приоритет можно
    сменить на любой в любой момент, поэтому здесь просто перечисление, не
    диаграмма состояний.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Разрешённые переходы статуса — правило живёт здесь, а не размазано по сервису.
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.REVIEW, TaskStatus.TODO},
    TaskStatus.REVIEW: {TaskStatus.DONE, TaskStatus.IN_PROGRESS},
    TaskStatus.DONE: set(),  # финальный статус; повторное открытие — через явный "reopen", Roadmap
}


@dataclass
class TaskEntity:
    id: UUID
    column_id: UUID
    project_id: UUID
    title: str
    status: TaskStatus
    position: int

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in ALLOWED_TRANSITIONS[self.status]
