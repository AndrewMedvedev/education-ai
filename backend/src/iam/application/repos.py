from uuid import UUID

from src.iam.domain.entities import Invitation, Membership, Permission, Role, ServiceAccount, User
from src.iam.domain.vo import Email
from src.shared.application.dtos import Page, Pagination
from src.shared.application.repos import Repository

from .dtos import PermissionQueryParamFilters


class UserRepository(Repository[User]):

    async def get_by_email(self, email: Email) -> User | None: ...


class ServiceAccountRepository(Repository[ServiceAccount]):

    async def get_by_client_id(self, client_id: str) -> ServiceAccount | None: ...


class MembershipRepository(Repository[Membership]):

    async def get_by_user(self, user_id: UUID) -> tuple[Membership, ...]: ...

    async def get_by_user_and_organization(
            self, user_id: UUID, organization_id: UUID,
    ) -> Membership | None: ...


class PermissionRepository:

    async def create_or_update(self, permission: ...) -> None: ...

    async def find(
            self, pagination: Pagination, filters: PermissionQueryParamFilters | None = None,
    ) -> Page[Permission]: ...


class RoleRepository(Repository[Role]):

    async def get_by_code(self, code: str) -> Role | None: ...


class InvitationRepository(Repository[Invitation]):

    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def get_active_by_email(self, email: Email) -> tuple[Invitation, ...]: ...
