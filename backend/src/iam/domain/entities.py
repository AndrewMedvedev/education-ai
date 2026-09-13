from typing import Annotated, Self

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from typing_extensions import Doc

from src.shared.domain.entities import Entity
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.domain.helpers import apply_changes
from src.shared.utils.time import current_datetime, get_expiration_time

from .events import UserInvited
from .types import RoleId
from .vo import Email, FullName, PermissionGrant, PermissionScope, SecretHash, Username

INVITATION_EXPIRES_IN_DAYS = 7


def _generate_invite_token(length: int = 32) -> str:
    """
    Генерирует токен для активации приглашения.
    """

    return secrets.token_urlsafe(length)


@dataclass(kw_only=True)
class User(Entity):
    """
    Пользователь системы (человек).

    User представляет физического пользователя независимо
    от организаций, в которых он состоит.

    Не содержит ролей или разрешений.

    Один пользователь может одновременно состоять
    в нескольких организациях через Membership и иметь
    в каждой из них собственный набор ролей.

    Отвечает только за:

    - аутентификацию;
    - персональные данные;
    - глобальный жизненный цикл учетной записи.
    """

    email: Email
    username: Username | None = None
    full_name: FullName | None = None
    avatar_url: str | None = None
    password_hash: SecretHash
    is_active: bool = True

    def deactivate(self) -> None:
        """Деактивировать учётную запись."""

        if not self.is_active:
            return

        self.is_active = False
        self.updated_at = current_datetime()


@dataclass(kw_only=True)
class ServiceAccount(Entity):
    """
    Сервисная учетная запись.

    Используется для машинной аутентификации
    (AI-агенты, интеграции, внешние сервисы,
    CLI, backend-to-backend взаимодействие).

    В отличие от User:

    - не принадлежит человеку;
    - использует client_id/client_secret;
    - всегда принадлежит одной организации;
    - получает роли аналогично Membership.

    После успешной аутентификации преобразуется
    в Subject так же, как и обычный пользователь.
    """

    name: str
    description: str | None = None

    client_id: str
    client_secret_hash: SecretHash

    organization_id: UUID

    roles: set[UUID]
    is_active: bool = True


@dataclass(kw_only=True)
class Membership(Entity):
    """
    Членство пользователя в организации.

    Membership является источником авторизации.

    Именно Membership определяет:

    • в какой организации работает пользователь;
    • какие роли действуют;
    • срок действия доступа;
    • активность доступа.

    Один User может иметь множество Membership.

    Пример:

        User
            ├── Membership (OpenAI)
            │      ├── Admin
            │      └── HR
            │
            └── Membership (Microsoft)
                   └── Viewer

    Все проверки доступа выполняются относительно
    конкретного Membership.
    """

    user_id: UUID
    organization_id: UUID
    roles: set[RoleId]
    expires_at: datetime | None = None
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.roles:
            raise InvariantViolationError("Membership must contain at least one role.")

        if self.is_expired and self.is_active:
            raise InvariantViolationError("Expired membership cannot be active.")

    @property
    def is_expired(self) -> None:
        return self.expires_at is not None and self.expires_at <= current_datetime()

    def extend(self, expires_at: datetime) -> None:
        """Продление сотрудничества на определённый срок."""

        self.expires_at = expires_at
        self.updated_at = current_datetime()

    def expire(self) -> None:
        """Досрочно завершить срок."""

        if self.expires_at and current_datetime() < self.expires_at:
            self.expires_at = current_datetime()
            self.updated_at = current_datetime()

    def has_role(self, role_id: RoleId) -> bool:
        return role_id in self.roles

    def has_any_role(self, roles: set[RoleId]) -> bool:
        return bool(self.roles & roles)

    def has_all_roles(self, roles: set[RoleId]) -> bool:
        return roles.issubset(self.roles)

    def grant_role(self, role_id: RoleId) -> None:

        if role_id in self.roles:
            return

        self.roles.add(role_id)
        self.updated_at = current_datetime()

    def revoke_role(self, role_id: RoleId) -> None:

        if role_id not in self.roles:
            return

        if len(self.roles) == 1:
            raise InvariantViolationError("Membership must contain at leat one role.")

        self.roles.remove(role_id)
        self.updated_at = current_datetime()


@dataclass(frozen=True, slots=True)
class Permission:
    """
    Разрешение на выполнение одного действия.
    Permission является минимальной единицей авторизации.

    Формируется из пары: resource + action

    Например: `task.read`, `task.update`, `task.delete`.

    Permission не является сущностью, так как полностью определяется своим кодом.
    """

    resource: str
    action: str

    title: str
    description: str | None = None

    scopes: frozenset[PermissionScope] = field(default_factory=frozenset)

    @property
    def code(self) -> str:
        return f"{self.resource}.{self.action}"


@dataclass(kw_only=True)
class Role(Entity):
    """"""

    name: str
    code: str
    description: str | None = None

    permissions: set[PermissionGrant]
    is_default: Annotated[bool, Doc("Является ли роль системной")] = False

    author_id: UUID | None = None
    organization_id: UUID | None = None

    def update(
            self,
            name: str | None = None,
            code: str | None = None,
            description: str | None = None,
    ) -> None:
        if self.is_default:
            raise InvariantViolationError("Default role cannot be updated.")

        apply_changes(self, name=name, code=code, description=description)

    def has_permission(self, permission: str, scope: PermissionScope) -> bool:
        return PermissionGrant(permission=permission, scope=scope) in self.permissions

    def grant_permission(self, grant: str, scope: PermissionScope) -> None:

        grant = PermissionGrant(permission=grant, scope=scope)
        if grant in self.permissions:
            return

        self.permissions.add(grant)
        self.updated_at = current_datetime()

    def revoke_permission(self, grant: str, scope: PermissionScope) -> None:

        grant = PermissionGrant(permission=grant, scope=scope)
        if grant not in self.permissions:
            return

        if len(self.permissions) == 1:
            raise InvariantViolationError("Role must contain a leat one grant.")

        self.permissions.discard(grant)
        self.updated_at = current_datetime()

    def remove(self) -> None:
        if self.is_default:
            raise InvariantViolationError("Default role cannot be deleted.")

        if self.is_deleted:
            return

        self.deleted_at = current_datetime()


@dataclass(kw_only=True)
class Invitation(Entity):
    """Приглашение пользователя в систему."""

    email: Email
    token: str = field(default_factory=_generate_invite_token)
    invited_by: UUID

    granted_roles: set[RoleId]
    organization_id: UUID
    expires_at: datetime

    used_at: datetime | None = None
    is_used: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.is_used and self.expires_at > current_datetime()

    @classmethod
    def create(
            cls,
            email: Email,
            invited_by: UUID,
            granted_roles: set[RoleId],
            organization_id: UUID,
    ) -> Self:
        expires_at = get_expiration_time(expires_in=timedelta(days=INVITATION_EXPIRES_IN_DAYS))
        invitation = cls(
            email=email,
            invited_by=invited_by,
            granted_roles=granted_roles,
            organization_id=organization_id,
            expires_at=expires_at,
        )
        invitation.invite()
        return invitation

    def invite(self) -> None:
        self.register_event(
            UserInvited(
                invitation_id=self.id,
                email=self.email,
                granted_roles=self.granted_roles,
                counterparty_id=self.organization_id,
                invited_by=self.invited_by,
            )
        )

    def mark_as_used(self) -> None:
        self.used_at = current_datetime()
        self.is_used = True
