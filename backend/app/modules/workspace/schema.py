"""Pydantic DTO модуля `workspace`."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.core.security.permissions import WorkspaceRole
from app.modules.users.schema import UserRead
from app.modules.workspace.model import InvitationStatus
from app.shared.schemas import IDMixin, ORMModel, TimestampMixin


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceRead(ORMModel, IDMixin, TimestampMixin):
    name: str
    slug: str
    owner_id: UUID


class WorkspaceMemberAdd(BaseModel):
    """Добавляет УЖЕ зарегистрированного пользователя напрямую — для
    незарегистрированных используется `InvitationCreate` (см. ниже).
    """

    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberRoleUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberRead(ORMModel, IDMixin):
    workspace_id: UUID
    role: WorkspaceRole
    joined_at: datetime
    user: UserRead


class InvitationCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class InvitationRead(ORMModel, IDMixin, TimestampMixin):
    workspace_id: UUID
    email: str
    role: WorkspaceRole
    invited_by: UUID
    expires_at: datetime
    status: InvitationStatus


class InvitationPublicRead(BaseModel):
    """Отдаётся без авторизации (GET /invitations/{token}) — только то, что
    нужно ещё не зарегистрированному приглашённому, чтобы решить, идти ли
    регистрироваться: без `invited_by`/`id` внутренних деталей.
    """

    workspace_name: str
    email: str
    role: WorkspaceRole
    status: InvitationStatus
