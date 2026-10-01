from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.application.dtos import Page, Pagination
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError

from ...application.repos import CourseRepository, MemberRepository
from ...domain.entities import Course, Member
from ...domain.vo import MemberRole


class MemberService:
    def __init__(
        self,
        member_repo: MemberRepository,
        course_repo: CourseRepository,
        session: AsyncSession,
    ):
        self._member_repo = member_repo
        self._course_repo = course_repo
        self._session = session

    async def sign_course(self, user_id: UUID, course_id: UUID) -> Member:
        course = await self._course_repo.exists(course_id)
        if not course:
            raise NotFoundError(f"Course with id {course_id} not found")
        student = await self._member_repo.read(user_id, course_id)
        if student is not None:
            raise AlreadyExistsError(
                f"Member with id {user_id} is already signed for course {course_id}"
            )
        student = Member(course_id=course_id, user_id=user_id, role=MemberRole.STUDENT)
        await self._member_repo.create(student)
        await self._session.commit()
        return student

    async def get_my_courses(self, user_id: UUID, pagination: Pagination) -> Page[Course]:
        return await self._course_repo.find_student_courses(user_id, pagination)
