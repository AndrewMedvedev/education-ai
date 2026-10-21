from uuid import UUID

from src.iam.application.dtos import Identity
from src.iam.application.policies import authorize
from src.iam.domain.entities import Permission
from src.shared.domain.exceptions import NotFoundError

from .policies import ManageCourseOptions
from .repos import (
    BasicInfoProtocol,
    MemberRepository,
)


class CheckAccess:
    def __init__(
        self,
        repo: BasicInfoProtocol,
        member_repo: MemberRepository,
    ) -> None:
        self._repo = repo

        self._member_repo = member_repo

    async def __call__(
        self,
        identity: Identity,
        permission: Permission,
        uid: UUID,
    ) -> None:
        ownership = await self._repo.read_course_ownership(uid)

        if ownership is None:
            raise NotFoundError("Course not found")

        course_id, creator_id = ownership

        role = await self._member_repo.read_role(identity.id, course_id)

        authorize(
            identity,
            permission,
            ManageCourseOptions(creator_id=creator_id, member_role=role),
        )
