from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.application.dtos import Page, Pagination
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError

from ...application.repos import CourseRepository, StudentRepository
from ...domain.entities import Course, Student


class StudentService:
    def __init__(
        self,
        student_repo: StudentRepository,
        course_repo: CourseRepository,
        session: AsyncSession,
    ):
        self._student_repo = student_repo
        self._course_repo = course_repo
        self._session = session

    async def sign_course(self, user_id: UUID, course_id: UUID) -> Student:
        course = await self._course_repo.exists(course_id)
        if not course:
            raise NotFoundError(f"Course with id {course_id} not found")
        student = await self._student_repo.read(user_id, course_id)
        if student is not None:
            raise AlreadyExistsError(
                f"Student with id {user_id} is already signed for course {course_id}"
            )
        student = Student(course_id=course_id, user_id=user_id)
        await self._student_repo.create(student)
        await self._session.commit()
        return student

    async def get_my_courses(self, user_id: UUID, pagination: Pagination) -> Page[Course]:
        return await self._course_repo.find_student_courses(user_id, pagination)
