import logging
from uuid import UUID

from src.courses.application.policies import InviteCourseOptions
from src.courses.domain.permissions.invitations import INVITE
from src.courses.domain.vo import MemberRole
from src.courses.infra.external_apis import get_user_by_email, invite_user_in_system
from src.courses.infra.services.client import SrvCourseClient
from src.iam.application.dtos import Identity
from src.iam.application.dtos import InvitationCreate as IAMInvitationCreate
from src.iam.application.policies import authorize
from src.iam.domain.entities import Permission
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.domain.repos import get_or_raise_404
from src.shared.domain.vo import Email

from ...domain.entities import Course, Invitation, Member
from ..dtos import InvitationCreate
from ..repos import CourseRepository, InvitationRepository, MemberRepository

logger = logging.getLogger(__name__)


class InvitationService:
    def __init__(
        self,
        transaction: Transaction,
        invitation_repo: InvitationRepository,
        course_repo: CourseRepository,
        member_repo: MemberRepository,
        client: SrvCourseClient,
    ) -> None:
        self.transaction = transaction
        self.invitation_repo = invitation_repo
        self.course_repo = course_repo
        self.member_repo = member_repo
        self.client = client

    async def _check_access(
        self,
        identity: Identity,
        permission: Permission,
        course_id: UUID,
        role: MemberRole,
    ) -> tuple[Course, Member | None]:
        course = await self.course_repo.read(course_id)
        member = await self.member_repo.read(identity.id, course_id)
        if course is None:
            raise NotFoundError
        authorize(
            identity,
            permission,
            InviteCourseOptions(
                course=course,
                member=member,
                role=role,
            ),
        )
        return course, member

    async def create(
        self,
        dto: InvitationCreate,
        identity: Identity,
    ) -> Invitation:
        """
        Создаёт приглашение + публикует событие для отправки на почту.
        """
        course, _ = await self._check_access(
            identity,
            permission=INVITE,
            course_id=dto.course_id,
            role=dto.role,
        )

        invitation = await self.invitation_repo.get_active(
            email=Email(dto.email),
            course_id=dto.course_id,
        )
        user = await get_user_by_email(dto.email, self.client)
        if user is None:
            await invite_user_in_system(
                dto=IAMInvitationCreate(email=dto.email),
                client=self.client,
            )
        if invitation is None:
            logger.info("Invitation is not found for email - `%s`, start creating new", dto.email)
            invitation = Invitation.create(
                title=course.title,
                course_id=course.id,
                email=Email(dto.email),
                user_id=user.id if user else None,
                role=dto.role,
                invited_by=identity.id,
            )
            await self.invitation_repo.create(invitation)
        elif invitation.is_valid:
            invitation.invite()
        await self.transaction(invitation)
        return invitation

    async def accept(self, token: str, user_id: UUID) -> Member:
        if (
            invitation := await self.invitation_repo.get_by_token(token)
        ) is None or not invitation.is_valid:
            raise NotFoundError(f"Invitation with token - '{token}' not found or invalid.")

        if await self.member_repo.exists(
            user_id=user_id,
            course_id=invitation.course_id,
        ):
            raise AlreadyExistsError("User is already a member of the course.")
        member = await self.member_repo.create(
            Member(
                role=invitation.role,
                course_id=invitation.course_id,
                user_id=user_id,
            )
        )
        invitation.mark_as_used()
        await self.transaction(member, invitation)
        return member

    async def revoke_invitation(self, invitation_id: UUID) -> None:
        """
        Отзыв ошибочно отправленного приглашения.
        """
        invitation = await get_or_raise_404(self.invitation_repo.read, invitation_id, Invitation)

        await self.invitation_repo.delete(invitation_id)
        await self.transaction(invitation)
        logger.info("Invitation deleted successfully")
