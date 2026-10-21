from uuid import UUID

from sqlalchemy import exists, func, select

from src.shared.application.dtos import Page, Pagination
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository, paginate

from ....domain.entities import CourseProgress
from ..mappers import CourseProgressMapper
from ..models import CourseProgressOrm, LessonProgressOrm


class SqlCourseProgressRepository(SqlAlchemyRepository[CourseProgress, CourseProgressOrm]):
    model = CourseProgressOrm
    model_mapper = CourseProgressMapper

    async def get_by_user(self, user_id: UUID, resource_id: UUID) -> CourseProgress | None:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.course_id == resource_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def exist_by_user(self, user_id: UUID, resource_id: UUID) -> bool:
        stmt = select(exists().where(
            self.model.user_id == user_id,
            self.model.course_id == resource_id,
        ))
        return bool(await self._session.scalar(stmt))

    async def count_completed_lessons(self, course_progress_id: UUID) -> int:
        completed_lessons = await self._session.scalar(
            select(func.count())
            .select_from(LessonProgressOrm)
            .where(
                LessonProgressOrm.module_progress.has(course_progress_id=course_progress_id),
                LessonProgressOrm.theory_completed_at.is_not(None),
                LessonProgressOrm.practice_completed_at.is_not(None),
                LessonProgressOrm.test_completed_at.is_not(None),
            )
        )
        return completed_lessons or 0

    async def find_by_course(self, course_id: UUID, pagination: Pagination) -> Page[CourseProgress]:
        """Возвращает progress всех учеников курса для teacher endpoint."""
        stmt = select(self.model).where(self.model.course_id == course_id)
        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,
            pagination=pagination,
            mapper=self.model_mapper.from_model,
            sort="created_at:desc",
        )
