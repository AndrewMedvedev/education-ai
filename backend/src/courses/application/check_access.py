from collections.abc import Awaitable, Callable
from uuid import UUID

from src.iam.application.dtos import Identity
from src.iam.application.policies import authorize
from src.iam.domain.entities import Permission
from src.shared.domain.exceptions import NotFoundError

from .policies import ManageCourseOptions
from .repos import CourseRepository, LessonRepository, MemberRepository, ModuleRepository


class CheckAccess:
    def __init__(
        self,
        course_repo: CourseRepository,
        member_repo: MemberRepository,
        module_repo: ModuleRepository,
        lesson_repo: LessonRepository,
    ) -> None:
        self._course_repo = course_repo
        self._member_repo = member_repo
        self._module_repo = module_repo
        self._lesson_repo = lesson_repo

    async def course(
        self,
        identity: Identity,
        permission: Permission,
        course_id: UUID,
    ) -> None:
        await self._authorize_course(identity, permission, course_id)

    async def module(
        self,
        identity: Identity,
        permission: Permission,
        module_id: UUID,
    ) -> None:
        await self._authorize_via(
            self._module_repo.read_course_id,
            identity,
            permission,
            module_id,
        )

    async def lesson(
        self,
        identity: Identity,
        permission: Permission,
        lesson_id: UUID,
    ) -> None:
        await self._authorize_via(
            self._lesson_repo.read_course_id,
            identity,
            permission,
            lesson_id,
        )

    async def _authorize_via(
        self,
        get_course_id: Callable[[UUID], Awaitable[UUID | None]],
        identity: Identity,
        permission: Permission,
        entity_id: UUID,
    ) -> None:
        course_id = await get_course_id(entity_id)
        if course_id is None:
            raise NotFoundError

        await self._authorize_course(identity, permission, course_id)

    async def _authorize_course(
        self,
        identity: Identity,
        permission: Permission,
        course_id: UUID,
    ) -> None:
        creator_id = await self._course_repo.read_creator_id(course_id)
        if creator_id is None:
            raise NotFoundError

        role = await self._member_repo.read_role(identity.id, course_id)

        authorize(
            identity,
            permission,
            ManageCourseOptions(creator_id=creator_id, member_role=role),
        )
