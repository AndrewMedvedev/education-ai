import logging
from uuid import UUID

from src.iam.domain.types import RoleId
from src.iam.domain.vo import Email
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.domain.repos import get_or_raise_404
from src.shared.utils.time import current_datetime

from ...domain.entities import Invitation
from ..dtos.invitations import InvitationCreate
from ..repos import InvitationRepository, RoleRepository

logger = logging.getLogger(__name__)


class InvitationService:
    def __init__(
        self,
        transaction: Transaction,
        invitation_repo: InvitationRepository,
        role_repo: RoleRepository,
    ) -> None:
        self.transaction = transaction
        self.invitation_repo = invitation_repo
        self.role_repo = role_repo

    @staticmethod
    def _is_same_invitation_scope(
        invitation: Invitation,
        organization_id: UUID | None,
        granted_roles: set[RoleId] | None,
    ) -> bool:
        return invitation.organization_id == organization_id and (
            invitation.granted_roles or set()
        ) == (granted_roles or set())

    async def create(
        self,
        dto: InvitationCreate,
        invited_by: UUID,
    ) -> Invitation:
        email = Email(dto.email)
        if dto.granted_roles is None:
            default_role = await self.role_repo.get_by_code("default_role")

            if default_role is None:
                raise NotFoundError(
                    "Default role with code 'default_role' was not found."
                )

            requested_roles = {RoleId(default_role.id)}
        else:
            requested_roles = dto.granted_roles

        invitations = await self.invitation_repo.get_active_by_email(email)
        invitation = next(
            (
                invitation
                for invitation in invitations
                if invitation.is_valid
                and self._is_same_invitation_scope(
                    invitation=invitation,
                    organization_id=dto.organization_id,
                    granted_roles=requested_roles,
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
            granted_roles=requested_roles,
            organization_id=dto.organization_id,
        )

        await self.invitation_repo.create(invitation)
        await self.transaction(invitation)

        return invitation

    async def revoke_invitation(
        self, invitation_id: UUID, organization_id: UUID
    ) -> None:
        """
        Отзыв ошибочно отправленного приглашения.
        """
        invitation = await get_or_raise_404(
            self.invitation_repo.read, invitation_id, Invitation
        )
        if invitation.organization_id != organization_id:
            raise NotFoundError("Invitation not found.")
        if invitation.deleted_at:
            return
        invitation = await self.invitation_repo.get_by_token(invitation.token)
        if invitation is None:
            raise NotFoundError("Invitation not found.")
        if invitation.is_used:
            raise AlreadyExistsError("Accepted invitations cannot be revoked.")
        await self.invitation_repo.update(invitation_id, deleted_at=current_datetime())
        await self.transaction(invitation)
        logger.info("Invitation deleted successfully")
