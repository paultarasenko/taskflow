"""RBAC-проверки прав доступа.

Роли зафиксированы в схеме БД (docs/01-architecture-and-design.md, раздел 4):
WORKSPACE_MEMBERS.role: owner|admin|member
PROJECT_MEMBERS.role: owner|editor|viewer

Полная реализация — Этап 6 (Users и Workspace), заглушка сейчас фиксирует
контракт, которым будут пользоваться сервисы модулей.
"""

from enum import StrEnum


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class ProjectRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


def require_workspace_role(actual: WorkspaceRole, minimum: WorkspaceRole) -> bool:
    """Проверяет, что роль пользователя не ниже требуемой.

    TODO(Этап 6): подключить к реальным сервисам workspace/projects.
    """
    order = [WorkspaceRole.MEMBER, WorkspaceRole.ADMIN, WorkspaceRole.OWNER]
    return order.index(actual) >= order.index(minimum)
