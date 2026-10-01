from dataclasses import dataclass
from uuid import UUID

from src.iam.domain.types import RoleId
from src.shared.domain.events import Event
from src.shared.domain.vo import Email


@dataclass(frozen=True, kw_only=True)
class OrganizationInvited(Event):
    """Приглашение в курс"""

    event_type: str = "organizations.invited"

    invitation_id: UUID
    invited_by: UUID
    email: Email
    granted_roles: set[RoleId]
    organization_id: UUID
    user_id: UUID | None = None
    url: str
