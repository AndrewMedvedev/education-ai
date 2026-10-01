from typing import Self

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from pydantic import EmailStr

from src.core.settings import settings
from src.iam.domain.entities import _generate_invite_token
from src.iam.domain.types import RoleId
from src.shared.domain.entities import AggregateRoot, Entity
from src.shared.domain.vo import Email
from src.shared.utils.time import current_datetime, get_expiration_time

from .events import OrganizationInvited

INVITATION_EXPIRES_IN_DAYS = 7


@dataclass(kw_only=True)
class Organization(AggregateRoot):
    name: str
    email: EmailStr
    description: str
    is_active: bool = True

    def edit(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        email: EmailStr | None = None,
    ) -> None:
        """
        Редактирование основных данных организации.
        """

        is_edited = False

        if name is not None and name.strip() and name.strip() != self.name:
            self.name = name.strip()
            is_edited = True

        if email is not None and email != self.email:
            self.email = email
            is_edited = True

        if (
            description is not None
            and description.strip()
            and description.strip() != self.description
        ):
            self.description = description.strip()
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()


@dataclass(kw_only=True)
class Invitation(Entity):
    """Приглашение пользователя в систему."""

    email: Email
    user_id: UUID | None = None
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
        user_id: UUID | None = None,
    ) -> Self:
        expires_at = get_expiration_time(expires_in=timedelta(days=INVITATION_EXPIRES_IN_DAYS))
        invitation = cls(
            email=email,
            user_id=user_id,
            invited_by=invited_by,
            granted_roles=granted_roles,
            organization_id=organization_id,
            expires_at=expires_at,
        )
        invitation.invite()
        return invitation

    def invite(self) -> None:
        self.register_event(
            OrganizationInvited(
                invitation_id=self.id,
                email=self.email,
                user_id=self.user_id,
                granted_roles=self.granted_roles,
                organization_id=self.organization_id,
                invited_by=self.invited_by,
                url=f"{settings.frontend_url}/auth/invite/accept/{self.token}",
            )
        )

    def mark_as_used(self) -> None:
        self.used_at = current_datetime()
        self.is_used = True
