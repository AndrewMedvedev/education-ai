from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from src.iam.application.repos import InvitationRepository as IAMInvitationRepository
from src.iam.application.repos import MembershipRepository, UserRepository
from src.iam.domain.entities import Membership
from src.organization.application.repos import InvitationRepository
from src.shared.application.dtos import Page, Pagination
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import (
    AlreadyExistsError,
    ForbiddenError,
    NotFoundError,
)
from src.shared.utils.time import current_datetime


class InvitationSummary(BaseModel):
    id: UUID
    source: Literal["iam", "organization"]
    email: str
    organization_id: UUID
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    status: Literal["pending", "accepted", "expired", "revoked"]


class InvitationManagementService:
    def __init__(
        self,
        organization_repo: InvitationRepository,
        iam_repo: IAMInvitationRepository,
        users: UserRepository,
        memberships: MembershipRepository,
        transaction: Transaction,
    ):
        self.repos = {"organization": organization_repo, "iam": iam_repo}
        self.users = users
        self.memberships = memberships
        self.transaction = transaction

    @staticmethod
    def summarize(invitation, source: str) -> InvitationSummary:
        status = "pending"
        if invitation.deleted_at:
            status = "revoked"
        elif invitation.is_used:
            status = "accepted"
        elif not invitation.is_valid:
            status = "expired"
        return InvitationSummary(
            id=invitation.id,
            source=source,
            email=invitation.email.value,
            organization_id=invitation.organization_id,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
            used_at=invitation.used_at,
            revoked_at=invitation.deleted_at,
            status=status,
        )

    async def list(
        self, organization_id: UUID, pagination: Pagination
    ) -> Page[InvitationSummary]:
        items = []
        for source, repo in self.repos.items():
            invitations = await repo.get_by_organization(organization_id)
            items.extend(
                self.summarize(invitation, source) for invitation in invitations
            )
        items.sort(key=lambda item: (item.created_at, str(item.id)), reverse=True)
        start = pagination.offset
        return Page.create(
            items[start : start + pagination.size],
            len(items),
            pagination.page,
            pagination.size,
        )

    async def get_scoped(self, invitation_id: UUID, source: str, organization_id: UUID):
        repo = self.repos[source]
        invitation = await repo.read(invitation_id)
        if invitation is None or invitation.organization_id != organization_id:
            raise NotFoundError("Invitation not found.")
        # Serialize changes with acceptance, including registration.
        if not invitation.deleted_at:
            invitation = await repo.get_by_token(invitation.token)
        if invitation is None:
            raise NotFoundError("Invitation not found.")
        return invitation, repo

    async def revoke(
        self, invitation_id: UUID, source: str, organization_id: UUID
    ) -> None:
        invitation, repo = await self.get_scoped(invitation_id, source, organization_id)
        if invitation.is_used:
            raise AlreadyExistsError("Accepted invitations cannot be revoked.")
        if not invitation.deleted_at:
            invitation.deleted_at = current_datetime()
            await repo.update(invitation.id, deleted_at=invitation.deleted_at)
            await self.transaction(invitation)

    async def resend(self, invitation_id: UUID, source: str, organization_id: UUID):
        invitation, _ = await self.get_scoped(invitation_id, source, organization_id)
        if invitation.deleted_at or invitation.is_used:
            raise AlreadyExistsError(
                "This invitation cannot be resent. Create a new invitation."
            )
        return invitation

    async def accept(self, token: str, user_id: UUID) -> Membership:
        invitation = None
        for repo in self.repos.values():
            invitation = await repo.get_by_token(token)
            if invitation is not None:
                break
        if invitation is None or invitation.deleted_at or not invitation.is_valid:
            raise NotFoundError("Invitation not found or invalid.")
        user = await self.users.read(user_id)
        if (
            user is None
            or user.email.value.casefold() != invitation.email.value.casefold()
        ):
            raise ForbiddenError("Invitation belongs to another email address.")
        if invitation.organization_id is None:
            raise NotFoundError("Organization invitation not found.")
        membership = await self.memberships.get_by_user_and_organization(
            user_id=user_id,
            organization_id=invitation.organization_id,
        )
        if membership is None:
            membership = Membership(
                user_id=user_id,
                organization_id=invitation.organization_id,
                roles=invitation.granted_roles,
            )
            await self.memberships.create(membership)
        invitation.mark_as_used()
        await repo.update(invitation.id, is_used=True, used_at=invitation.used_at)
        await self.transaction(invitation, membership)
        return membership
