import logging
from uuid import UUID

from src.iam.domain.types import RoleId
from src.iam.domain.vo import Email
from src.shared.application.transaction import Transaction
from src.shared.domain.repos import get_or_raise_404

from ...domain.entities import Invitation
from ..dtos.invitations import InvitationCreate
from ..repos import InvitationRepository

logger = logging.getLogger(__name__)


class InvitationService:
    def __init__(
        self,
        transaction: Transaction,
        invitation_repo: InvitationRepository,
    ) -> None:
        self.transaction = transaction
        self.invitation_repo = invitation_repo

    @staticmethod
    def _is_same_invitation_scope(
        invitation: Invitation,
        organization_id: UUID | None,
        granted_roles: set[RoleId] | None,
    ) -> bool:
        return invitation.organization_id == organization_id and (
            invitation.granted_roles or []
        ) == (granted_roles or [])

    async def create(
        self,
        dto: InvitationCreate,
        invited_by: UUID,
    ) -> Invitation:
        email = Email(dto.email)
        requested_roles = set(dto.granted_roles or set())
        invitations = await self.invitation_repo.get_active_by_email(email)
        invitation = next(
            (
                invitation
                for invitation in invitations
                if invitation.is_valid
                and self._is_same_invitation_scope(
                    invitation=invitation,
                    organization_id=dto.organization_id,
                    granted_roles=dto.granted_roles,
                )
            ),
            None,
        )

        if invitation is not None:
            logger.info(
                "Valid invitation already exists for email `%s`, organization `%s`, roles `%s`; resend invite",  # noqa: E501
                dto.email,
                dto.organization_id,
                requested_roles,
            )

            invitation.invite()
            await self.transaction(invitation)
            return invitation

        logger.info(
            "Valid invitation is not found for email `%s`, organization `%s`, roles `%s`; creating new",  # noqa: E501
            dto.email,
            dto.organization_id,
            requested_roles,
        )
        invitation = Invitation.create(
            email=email,
            invited_by=invited_by,
            granted_roles=requested_roles or None,
            organization_id=dto.organization_id,
        )

        await self.invitation_repo.create(invitation)
        await self.transaction(invitation)

        return invitation

    async def revoke_invitation(self, invitation_id: UUID) -> None:
        """
        Отзыв ошибочно отправленного приглашения.
        """
        invitation = await get_or_raise_404(self.invitation_repo.read, invitation_id, Invitation)

        await self.invitation_repo.delete(invitation_id)
        await self.transaction(invitation)
        logger.info("Invitation deleted successfully")
