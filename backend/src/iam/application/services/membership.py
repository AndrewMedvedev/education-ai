import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.application.dtos.membership import CreateMembershipDTO
from src.iam.domain.entities import Membership
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError

from ..repos import MembershipRepository, UserRepository

logger = logging.getLogger(__name__)


class MembershipService:
    def __init__(
        self,
        session: AsyncSession,
        membership_repo: MembershipRepository,
        user_repo: UserRepository,
    ) -> None:
        self.session = session
        self.membership_repo = membership_repo
        self.user_repo = user_repo

    async def create(
        self,
        dto: CreateMembershipDTO,
    ) -> Membership:
        user_exists = await self.user_repo.exists(dto.user_id)
        if not user_exists:
            raise NotFoundError("User not found")
        created_membership = await self.membership_repo.get_by_user_and_organization(
            dto.user_id,
            dto.organization_id,
        )
        if created_membership is not None:
            raise AlreadyExistsError("Membership already exists")
        membership = await self.membership_repo.create(
            Membership(
                user_id=dto.user_id,
                organization_id=dto.organization_id,
                roles=dto.roles,
                expires_at=dto.expires_at,
            )
        )
        await self.session.commit()
        return membership
