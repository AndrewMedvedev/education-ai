from typing import Annotated

from fastapi import Depends

from src.iam.dependencies.repos import (
    InvitationRepositoryDep,
    MembershipRepositoryDep,
    UserRepositoryDep,
)
from src.organization.application.repos import IAMRepository, MembershipRepository
from src.organization.application.services.invitation_management import (
    InvitationManagementService,
)
from src.organization.application.services.invitations import InvitationService
from src.organization.application.services.organizations import OrganizationService
from src.organization.infra.external_apis import IAMClient, MembershipClient
from src.organization.infra.services import organization_client
from src.shared.dependencies import DBSession, TransactionDep

from .base import InvitationRepoDep, OrganizationRepoDep


def get_organization_service(
    session: DBSession,
    repo: OrganizationRepoDep,
) -> OrganizationService:
    return OrganizationService(session, repo)


def get_membership_client() -> MembershipRepository:
    return MembershipClient(organization_client)


def get_iam_repo() -> IAMRepository:
    return IAMClient(organization_client)


MembershipClientDep = Annotated[MembershipClient, Depends(get_membership_client)]
IAMRepoDep = Annotated[IAMClient, Depends(get_iam_repo)]


def get_invitation_service(
    transaction: TransactionDep,
    invitation_repo: InvitationRepoDep,
    membership_repo: MembershipClientDep,
    iam_repo: IAMRepoDep,
) -> InvitationService:
    return InvitationService(
        transaction=transaction,
        invitation_repo=invitation_repo,
        membership_repo=membership_repo,
        iam_repo=iam_repo,
        client=organization_client,
    )


OrganizationServiceDep = Annotated[
    OrganizationService, Depends(get_organization_service)
]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]


def get_invitation_management(
    organization_repo: InvitationRepoDep,
    iam_repo: InvitationRepositoryDep,
    users: UserRepositoryDep,
    memberships: MembershipRepositoryDep,
    transaction: TransactionDep,
) -> InvitationManagementService:
    return InvitationManagementService(
        organization_repo, iam_repo, users, memberships, transaction
    )


InvitationManagementDep = Annotated[
    InvitationManagementService, Depends(get_invitation_management)
]
