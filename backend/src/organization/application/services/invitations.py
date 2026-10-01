import logging
from uuid import UUID

from src.iam.application.dtos import InvitationCreate as IAMInvitationCreate
from src.iam.application.dtos.membership import CreateMembershipDTO
from src.iam.domain.entities import Membership
from src.organization.application.dtos import InvitationCreate
from src.organization.domain.entities import Invitation
from src.organization.infra.services.client import SrvOrganizationClient
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.domain.repos import get_or_raise_404
from src.shared.domain.vo import Email

from ..repos import (
    IAMInvitationRepository,
    InvitationRepository,
    MembershipRepository,
    UserRepository,
)

logger = logging.getLogger(__name__)


class InvitationService:
    def __init__(
        self,
        transaction: Transaction,
        invitation_repo: InvitationRepository,
        membership_repo: MembershipRepository,
        user_repo: UserRepository,
        iam_invitation_repo: IAMInvitationRepository,
        client: SrvOrganizationClient,
    ) -> None:
        self.transaction = transaction
        self.invitation_repo = invitation_repo
        self.membership_repo = membership_repo
        self.user_repo = user_repo
        self.iam_invitation_repo = iam_invitation_repo
        self.client = client

    async def create(
        self,
        dto: InvitationCreate,
        invited_by: UUID,
    ) -> Invitation:
        invitation = await self.invitation_repo.get_active_by_email_and_organization(
            email=Email(dto.email),
            organization_id=dto.organization_id,
        )
        user = await self.user_repo(dto.email, self.client)
        if user is None:
            await self.iam_invitation_repo(
                IAMInvitationCreate(email=dto.email, granted_roles=dto.granted_roles),
                self.client,
            )
        else:
            membership = await self.membership_repo.get_user_membership(
                user.id,
                dto.organization_id,
            )
            if membership is not None:
                raise AlreadyExistsError("User already has a membership in this organization")
        if invitation is None or not invitation.is_valid:
            invitation = Invitation.create(
                email=Email(dto.email),
                invited_by=invited_by,
                granted_roles=dto.granted_roles,
                user_id=user.id if user is not None else None,
                organization_id=dto.organization_id,
            )

            await self.invitation_repo.create(invitation)
        else:
            invitation.invite()
        await self.transaction(invitation)
        return invitation

    async def accept(self, token: str, user_id: UUID) -> Membership:
        if (
            invitation := await self.invitation_repo.get_by_token(token)
        ) is None or not invitation.is_valid:
            raise NotFoundError(f"Invitation with token - '{token}' not found or invalid.")
        existing_membership = await self.membership_repo.get_user_membership(
            user_id,
            invitation.organization_id,
        )
        if existing_membership is not None:
            raise AlreadyExistsError("User is already a member of the course.")
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
