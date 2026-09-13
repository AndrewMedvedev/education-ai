from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event

from .types import RoleId
from .vo import Email


@dataclass(frozen=True, kw_only=True)
class UserInvited(Event):
    """
    Пользователю отправлено приглашение.
    """

    invitation_id: UUID
    email: Email
    granted_roles: set[RoleId]
    counterparty_id: UUID | None = None
    invited_by: UUID
