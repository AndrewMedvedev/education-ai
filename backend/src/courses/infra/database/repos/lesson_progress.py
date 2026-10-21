from uuid import UUID

from sqlalchemy import exists, select, update

from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ....domain.entities import LessonProgress
from ....domain.events import LessonProgressUpdated
from ..mappers import LessonProgressMapper
from ..models import CourseProgressOrm, LessonProgressOrm, ModuleProgressOrm


class SqlLessonProgressRepository(SqlAlchemyRepository[LessonProgress, LessonProgressOrm]):
    model = LessonProgressOrm
    model_mapper = LessonProgressMapper

    async def get_by_user(self, user_id: UUID, resource_id: UUID) -> LessonProgress | None:
        stmt = (
            select(self.model)
            .join(self.model.module_progress)
            .join(ModuleProgressOrm.course_progress)
            .where(
                CourseProgressOrm.user_id == user_id,
                self.model.lesson_id == resource_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def exist_by_user(self, user_id: UUID, resource_id: UUID) -> bool:
        stmt = select(exists().where(
            self.model.module_progress.has(
                ModuleProgressOrm.course_progress.has(user_id=user_id)
            ),
            self.model.lesson_id == resource_id,
        ))
        return bool(await self._session.scalar(stmt))

    async def update_from_event(self, event: LessonProgressUpdated) -> None:
        """Обновляет прогресс урока по событию."""
        stmt = (
            update(LessonProgressOrm)
            .where(
                LessonProgressOrm.lesson_id == event.lesson_id,
                LessonProgressOrm.module_progress.has(
                    ModuleProgressOrm.course_progress.has(user_id=event.user_id)
                ),
            )
            .values(**event.progress.model_dump(exclude_none=True))
        )
        await self._session.execute(stmt)
