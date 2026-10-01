from typing import Annotated

from fastapi import Depends

from src.organization.application.repos import IAMInvitationRepository, UserRepository
from src.organization.application.services.invitations import InvitationService
from src.organization.application.services.organizations import OrganizationService
from src.organization.infra.external_apis import (
    MembershipClient,
    get_user_by_email,
    invite_user_in_system,
)
from src.organization.infra.services import organization_client
from src.shared.dependencies import DBSession, TransactionDep

from .base import InvitationRepoDep, OrganizationRepoDep


def get_organization_service(
    session: DBSession,
    repo: OrganizationRepoDep,
) -> OrganizationService:
    return OrganizationService(session, repo)


def get_membership_client() -> MembershipClient:
    return MembershipClient(organization_client)


def get_user_repo() -> UserRepository:
    return get_user_by_email


def get_iam_invitation_repo() -> IAMInvitationRepository:
    return invite_user_in_system


MembershipClientDep = Annotated[MembershipClient, Depends(get_membership_client)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
IAMInvitationRepoDep = Annotated[IAMInvitationRepository, Depends(get_iam_invitation_repo)]


def get_invitation_service(
    transaction: TransactionDep,
    invitation_repo: InvitationRepoDep,
    membership_repo: MembershipClientDep,
    user_repo: UserRepoDep,
    iam_invitation_repo: IAMInvitationRepoDep,
) -> InvitationService:
    return InvitationService(
        transaction=transaction,
        invitation_repo=invitation_repo,
        membership_repo=membership_repo,
        user_repo=user_repo,
        iam_invitation_repo=iam_invitation_repo,
        client=organization_client,
    )


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]
