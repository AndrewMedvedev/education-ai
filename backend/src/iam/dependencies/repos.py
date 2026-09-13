from typing import Annotated

from fastapi import Depends

from src.core.redis import redis_client
from src.iam.application.repos import (
    InvitationRepository,
    MembershipRepository,
    PermissionRepository,
    RoleRepository,
    ServiceAccountRepository,
    UserRepository,
)
from src.iam.infra.database.repos import (
    SqlInvitationRepository,
    SqlMembershipRepository,
    SqlPermissionRepository,
    SqlRoleRepository,
    SqlServiceAccountRepository,
    SqlUserRepository,
)
from src.organization.application.repos import OrganizationRepository
from src.organization.infra.repos import SqlOrganizationRepository
from src.shared.dependencies import DBSession
from src.shared.infra.cache import Cache, PrimitiveSerializer, RedisCache

redis_cache = RedisCache[bool](redis_client, serializer=PrimitiveSerializer(bool))


def get_cache() -> Cache[bool]:
    return redis_cache


def get_user_repository(session: DBSession) -> UserRepository:
    return SqlUserRepository(session)


def get_service_account_repository(session: DBSession) -> ServiceAccountRepository:
    return SqlServiceAccountRepository(session)


def get_membership_repository(session: DBSession) -> MembershipRepository:
    return SqlMembershipRepository(session)


def get_role_repository(session: DBSession) -> RoleRepository:
    return SqlRoleRepository(session)


def get_permission_repository(session: DBSession) -> PermissionRepository:
    return SqlPermissionRepository(session)


def get_invitation_repository(session: DBSession) -> InvitationRepository:
    return SqlInvitationRepository(session)


def get_organization_repository(session: DBSession) -> OrganizationRepository:
    return SqlOrganizationRepository(session)


CacheDep = Annotated[Cache[bool], Depends(get_cache)]

UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
ServiceAccountRepositoryDep = Annotated[
    ServiceAccountRepository,
    Depends(get_service_account_repository),
]
MembershipRepositoryDep = Annotated[MembershipRepository, Depends(get_membership_repository)]
PermissionRepositoryDep = Annotated[PermissionRepository, Depends(get_permission_repository)]
RoleRepositoryDep = Annotated[RoleRepository, Depends(get_role_repository)]
InvitationRepositoryDep = Annotated[InvitationRepository, Depends(get_invitation_repository)]
OrganizationRepositoryDep = Annotated[OrganizationRepository, Depends(get_organization_repository)]
