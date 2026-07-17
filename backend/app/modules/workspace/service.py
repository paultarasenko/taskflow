"""Бизнес-логика модуля `workspace`."""

import re
import secrets
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.security.permissions import WorkspaceRole, require_workspace_role
from app.modules.users.model import User
from app.modules.users.repository import PostgresUserRepository
from app.modules.workspace.model import Invitation, InvitationStatus, Workspace, WorkspaceMember
from app.modules.workspace.repository import (
    PostgresInvitationRepository,
    PostgresWorkspaceMemberRepository,
    PostgresWorkspaceRepository,
)
from app.modules.workspace.schema import InvitationCreate, WorkspaceMemberAdd


def _slugify(name: str) -> str:
    """Простой slugify + случайный суффикс — гарантирует уникальность без
    цикла retry-на-конфликт (см. UniqueConstraint на `workspaces.slug`).
    Полноценная библиотека (python-slugify) была бы избыточна ради одной
    функции такого размера.
    """
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
    return f"{base}-{secrets.token_hex(3)}"


class WorkspaceService:
    """Приглашения (Invitation) намеренно остались в этом же сервисе, а не
    вынесены в отдельный InvitationService: концептуально это то же самое
    управление членством в workspace, просто отложенное во времени. Если
    когда-нибудь появится третий похожий сценарий (например, приглашения в
    project), тогда и есть смысл выносить общую логику — сейчас это было бы
    преждевременной абстракцией.
    """

    def __init__(
        self,
        workspace_repository: PostgresWorkspaceRepository,
        member_repository: PostgresWorkspaceMemberRepository,
        user_repository: PostgresUserRepository,
        invitation_repository: PostgresInvitationRepository,
    ) -> None:
        self._workspaces = workspace_repository
        self._members = member_repository
        self._users = user_repository
        self._invitations = invitation_repository

    # --- Workspace ---

    async def create(self, name: str, owner: User) -> Workspace:
        workspace = await self._workspaces.add(
            Workspace(name=name, slug=_slugify(name), owner_id=owner.id)
        )
        await self._members.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER)
        )
        return workspace

    async def list_for_user(
        self, user: User, limit: int, offset: int
    ) -> tuple[Sequence[Workspace], int]:
        return await self._workspaces.list_for_user(user.id, limit=limit, offset=offset)

    async def get_by_id(self, workspace_id: UUID) -> Workspace:
        """Доступ уже проверен на уровне роутера (`require_workspace_member`
        dependency) — здесь только бизнес-логика получения ресурса.
        """
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundError(f"Workspace {workspace_id} не найден")
        return workspace

    # --- Members ---

    @staticmethod
    def _require_admin(actor_role: WorkspaceRole) -> None:
        if not require_workspace_role(actor_role, WorkspaceRole.ADMIN):
            raise PermissionDeniedError("Требуется роль Admin или Owner")

    async def list_members(
        self, workspace_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[WorkspaceMember], int]:
        return await self._members.list_by_workspace(workspace_id, limit=limit, offset=offset)

    async def add_member(
        self, workspace_id: UUID, data: WorkspaceMemberAdd, actor_role: WorkspaceRole
    ) -> WorkspaceMember:
        self._require_admin(actor_role)

        user = await self._users.get_by_email(data.email)
        if user is None:
            raise NotFoundError(
                f"Пользователь с email {data.email!r} не зарегистрирован — "
                "используйте приглашение (POST /workspaces/{workspace_id}/invitations) "
                "для незарегистрированных пользователей"
            )

        existing = await self._members.get_membership(workspace_id, user.id)
        if existing is not None:
            raise ConflictError(f"Пользователь {data.email!r} уже участник этого workspace")

        new_member = await self._members.add(
            WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=data.role)
        )
        # Присваиваем вручную — избегаем ленивой подгрузки `.user` в
        # синхронном контексте Pydantic-валидации ответа (см. docstring
        # PostgresWorkspaceMemberRepository.get_membership).
        new_member.user = user
        return new_member

    async def change_member_role(
        self,
        workspace_id: UUID,
        target_user_id: UUID,
        new_role: WorkspaceRole,
        actor_role: WorkspaceRole,
    ) -> WorkspaceMember:
        self._require_admin(actor_role)

        membership = await self._members.get_membership(workspace_id, target_user_id)
        if membership is None:
            raise NotFoundError("Участник не найден в этом workspace")
        if membership.role == WorkspaceRole.OWNER or new_role == WorkspaceRole.OWNER:
            raise PermissionDeniedError(
                "Смена роли владельца (в т.ч. назначение нового) через этот эндпоинт "
                "не поддерживается — передача владения остаётся Roadmap"
            )

        membership.role = new_role
        return await self._members.save(membership)

    async def remove_member(
        self,
        workspace_id: UUID,
        target_user_id: UUID,
        actor_id: UUID,
        actor_role: WorkspaceRole,
    ) -> None:
        membership = await self._members.get_membership(workspace_id, target_user_id)
        if membership is None:
            raise NotFoundError("Участник не найден в этом workspace")
        if membership.role == WorkspaceRole.OWNER:
            raise PermissionDeniedError("Owner не может быть удалён из workspace")

        is_self_removal = target_user_id == actor_id
        if not is_self_removal:
            self._require_admin(actor_role)

        await self._members.delete(membership)

    # --- Invitations ---

    async def create_invitation(
        self,
        workspace_id: UUID,
        data: InvitationCreate,
        actor_id: UUID,
        actor_role: WorkspaceRole,
    ) -> Invitation:
        self._require_admin(actor_role)

        existing_user = await self._users.get_by_email(data.email)
        if existing_user is not None:
            existing_membership = await self._members.get_membership(workspace_id, existing_user.id)
            if existing_membership is not None:
                raise ConflictError(f"Пользователь {data.email!r} уже участник этого workspace")

        pending = await self._invitations.get_pending_for_email(workspace_id, data.email)
        if pending is not None:
            raise ConflictError(f"Приглашение для {data.email!r} уже отправлено и ещё активно")

        invitation = Invitation(
            workspace_id=workspace_id,
            email=data.email,
            role=data.role,
            token=Invitation.generate_token(),
            invited_by=actor_id,
            expires_at=Invitation.default_expiry(),
        )
        return await self._invitations.add(invitation)

    async def get_invitation_by_token(self, token: str) -> tuple[Invitation, Workspace]:
        """Возвращает и Invitation, и Workspace вместе — `InvitationPublicRead`
        (см. schema.py) отдаёт `workspace_name`, а не `workspace_id`: человек
        без аккаунта смотрит на понятное имя, а не на UUID.
        """
        invitation = await self._invitations.get_by_token(token)
        if invitation is None:
            raise NotFoundError("Приглашение не найдено")
        workspace = await self._workspaces.get_by_id(invitation.workspace_id)
        if workspace is None:  # pragma: no cover — workspace всегда есть, FK-гарантия
            raise NotFoundError("Workspace приглашения не найден")
        return invitation, workspace

    async def accept_invitation(self, token: str, current_user: User) -> WorkspaceMember:
        invitation, _workspace = await self.get_invitation_by_token(token)

        if invitation.email != current_user.email:
            raise PermissionDeniedError(
                "Приглашение выписано на другой email — войдите под "
                f"{invitation.email!r}, чтобы принять его"
            )
        if invitation.status != InvitationStatus.PENDING:
            raise ConflictError(f"Приглашение недоступно для принятия: статус {invitation.status}")

        existing = await self._members.get_membership(invitation.workspace_id, current_user.id)
        if existing is not None:
            raise ConflictError("Вы уже участник этого workspace")

        invitation.accepted_at = datetime.now(UTC)
        await self._invitations.save(invitation)

        new_member = await self._members.add(
            WorkspaceMember(
                workspace_id=invitation.workspace_id,
                user_id=current_user.id,
                role=invitation.role,
            )
        )
        new_member.user = current_user
        return new_member
