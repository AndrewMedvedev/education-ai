from typing import Protocol

from uuid import UUID

from src.iam.application.dtos import InvitationCreate, UserResponse
from src.iam.application.dtos.membership import CreateMembershipDTO
from src.iam.domain.entities import Invitation as IAMInvitation
from src.iam.domain.entities import Membership
from src.organization.infra.services.client import SrvOrganizationClient
from src.shared.application.repos import Repository
from src.shared.domain.vo import Email

from ..domain.entities import Invitation, Organization


class OrganizationRepository(Repository[Organization]):
    async def get_by_email(self, email: str) -> Organization | None: ...


class InvitationRepository(Repository[Invitation]):
    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def get_active_by_email(self, email: Email) -> tuple[Invitation, ...]: ...

    async def get_active_by_email_and_organization(
        self,
        email: Email,
        organization_id: UUID,
    ) -> Invitation | None: ...


class UserRepository(Protocol):
    async def __call__(
        self,
        email: str,
        client: SrvOrganizationClient,
    ) -> UserResponse | None: ...


class IAMInvitationRepository(Protocol):
    async def __call__(
        self,
        dto: InvitationCreate,
        client: SrvOrganizationClient,
    ) -> IAMInvitation | None: ...


class MembershipRepository(Protocol):
    async def create_membership(self, dto: CreateMembershipDTO) -> Membership: ...

    async def get_user_membership(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> Membership | None: ...
