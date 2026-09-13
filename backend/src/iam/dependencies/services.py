from typing import Annotated

from fastapi import Depends

from src.iam.application.services import (
    AuthService,
    ClientCredentialsService,
    OAuthService,
    RegistrationService,
)
from src.shared.dependencies import DBSession, TransactionDep

from .repos import (
    CacheDep,
    InvitationRepositoryDep,
    MembershipRepositoryDep,
    OrganizationRepositoryDep,
    RoleRepositoryDep,
    ServiceAccountRepositoryDep,
    UserRepositoryDep,
)


def get_auth_service(
    user_repo: UserRepositoryDep,
    membership_repo: MembershipRepositoryDep,
    role_repo: RoleRepositoryDep,
    organization_repo: OrganizationRepositoryDep,
    cache: CacheDep,
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        membership_repo=membership_repo,
        role_repo=role_repo,
        organization_repo=organization_repo,
        cache=cache,
    )


def get_oauth_service(
    service_account_repo: ServiceAccountRepositoryDep,
    role_repo: RoleRepositoryDep,
) -> OAuthService:
    return OAuthService(service_account_repo=service_account_repo, role_repo=role_repo)


def get_registration_service(
    transaction: TransactionDep,
    user_repo: UserRepositoryDep,
    membership_repo: MembershipRepositoryDep,
    role_repo: RoleRepositoryDep,
    invitation_repo: InvitationRepositoryDep,
) -> RegistrationService:
    return RegistrationService(
        transaction=transaction,
        user_repo=user_repo,
        membership_repo=membership_repo,
        role_repo=role_repo,
        invitation_repo=invitation_repo,
    )


def get_client_credentials_service(
    uow: DBSession,
    organization_repo: OrganizationRepositoryDep,
    service_account_repo: ServiceAccountRepositoryDep,
    role_repo: RoleRepositoryDep,
) -> ClientCredentialsService:
    return ClientCredentialsService(
        uow=uow,
        organization_repo=organization_repo,
        service_account_repo=service_account_repo,
        role_repo=role_repo,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]
RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]
ClientCredentialsServiceDep = Annotated[
    ClientCredentialsService,
    Depends(get_client_credentials_service),
]
