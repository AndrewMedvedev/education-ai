# pyright: reportArgumentType=false


from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import NotFoundError

from ...application.dtos import (
    CourseSchema,
    EditCourseSchema,
)
from ...domain.entities import Course
from ...domain.vo import CourseStatus
from ..repos import (
    CourseRepository,
)
from .base_course import BaseCourseService


class CourseService(BaseCourseService[CourseRepository]):
    def __init__(self, repo: CourseRepository, session: AsyncSession) -> None:
        super().__init__(repo=repo, session=session)

    async def create(self, user_id: UUID, schema: CourseSchema) -> Course:
        """Создаёт курс и инкапсулирует правила этой операции."""
        course = await self.repo.create(Course(creator_id=user_id, **schema.model_dump()))
        await self.session.commit()
        return course

    async def edit(self, course_id: UUID, schema: EditCourseSchema) -> Course:
        """Выполняет действие `edit_course`, чтобы поддержать основной сценарий модуля."""
        course_exists = await self.repo.exists(course_id)
        if not course_exists:
            raise NotFoundError(f"Course with id {course_id} not found")
        course = await self.repo.update(uid=course_id, **schema.model_dump(exclude_none=True))
        await self.session.commit()
        return course

    async def delete(self, course_id: UUID) -> None:
        course_exists = await self.repo.exists(course_id)
        if not course_exists:
            raise NotFoundError(f"Course with id {course_id} not found")
        await self.repo.delete(course_id)
        await self.session.commit()

    async def change_status(self, course_id: UUID, status: CourseStatus) -> None:
        course_exists = await self.repo.exists(course_id)
        if not course_exists:
            raise NotFoundError(f"Course with id {course_id} not found")
        await self.repo.update(uid=course_id, status=status)
        await self.session.commit()
