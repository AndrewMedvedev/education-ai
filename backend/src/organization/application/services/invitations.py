import logging
from uuid import UUID

from src.iam.application.dtos import Identity
from src.iam.application.dtos import InvitationCreate as IAMInvitationCreate
from src.iam.application.dtos.membership import CreateMembershipDTO
from src.iam.domain.entities import (
    Invitation as IAMInvitation,
)
from src.iam.domain.entities import Membership
from src.organization.application.dtos import InvitationCreate
from src.organization.domain.entities import Invitation
from src.organization.infra.services.client import SrvOrganizationClient
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.domain.repos import get_or_raise_404
from src.shared.domain.vo import Email

from ..repos import (
    IAMRepository,
    InvitationRepository,
    MembershipRepository,
)

logger = logging.getLogger(__name__)


class InvitationService:
    def __init__(
        self,
        transaction: Transaction,
        invitation_repo: InvitationRepository,
        membership_repo: MembershipRepository,
        iam_repo: IAMRepository,
        client: SrvOrganizationClient,
    ) -> None:
        self.transaction = transaction
        self.invitation_repo = invitation_repo
        self.membership_repo = membership_repo
        self.iam_repo = iam_repo
        self.client = client

    async def create(
        self,
        dto: InvitationCreate,
        identity: Identity,
    ) -> Invitation | IAMInvitation:
        invitation = await self.invitation_repo.get_active_by_email_and_organization(
            email=Email(dto.email),
            organization_id=identity.organization_id,
        )
        user = await self.iam_repo.get_user_by_email(dto.email)
        if user is None:
            return await self.iam_repo.invite_user_in_system(
                IAMInvitationCreate(
                    email=dto.email,
                    granted_roles=dto.granted_roles,
                    organization_id=identity.organization_id,
                ),
            )
        membership = await self.membership_repo.get_user_membership(
            user_id=user.id,
            organization_id=identity.organization_id,
        )
        if membership is not None:
            raise AlreadyExistsError("User already has a membership in this organization")
        if invitation is None or not invitation.is_valid:
            invitation = Invitation.create(
                email=Email(dto.email),
                invited_by=identity.id,
                granted_roles=dto.granted_roles,
                user_id=user.id if user is not None else None,
                organization_id=identity.organization_id,
            )

            await self.invitation_repo.create(invitation)
        else:
            invitation.invite()
        await self.transaction(invitation)
        return invitation

    async def accept(self, token: str, user_id: UUID) -> Membership:
        invitation = await self.invitation_repo.get_by_token(token)

        if invitation is None or not invitation.is_valid:
            raise NotFoundError(f"Invitation with token - '{token}' not found or invalid.")

        membership = await self.membership_repo.get_user_membership(
            organization_id=invitation.organization_id,
            user_id=user_id,
        )

        if membership is not None:
            raise AlreadyExistsError("User already has a membership in this organization.")

        membership = await self.membership_repo.create_membership(
            CreateMembershipDTO(
                user_id=user_id,
                organization_id=invitation.organization_id,
                roles=invitation.granted_roles,
            )
        )

        invitation.mark_as_used()
        await self.transaction(invitation)

        return membership

    async def revoke_invitation(self, invitation_id: UUID) -> None:
        """
        Отзыв ошибочно отправленного приглашения.
        """
        invitation = await get_or_raise_404(self.invitation_repo.read, invitation_id, Invitation)

        await self.invitation_repo.delete(invitation_id)
        await self.transaction(invitation)
        logger.info("Invitation deleted successfully")
