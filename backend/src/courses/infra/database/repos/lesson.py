from typing import Any

import logging
from uuid import UUID

from sqlalchemy import func, literal, select, text, update
from sqlalchemy.dialects.postgresql import JSONB

from src.courses.application.dtos import LessonBasicInfo
from src.courses.domain.entities import (
    AnyContentBlock,
    Lesson,
)
from src.shared.domain.exceptions import NotFoundError
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ..mappers import (
    LessonMapper,
)
from ..models import CourseOrm, LessonOrm, ModuleOrm

logger = logging.getLogger(__name__)


class SqlLessonRepository(SqlAlchemyRepository[Lesson, LessonOrm]):
    model = LessonOrm
    model_mapper = LessonMapper  # type: ignore

    async def create_at(self, lesson: Lesson) -> Lesson:
        if lesson.order < 1:
            raise ValueError("Lesson order must be greater than 0")
        if lesson.module_id is None:
            raise ValueError("module_id is required")

        locked = await self._session.scalar(
            select(ModuleOrm.id)
            .where(ModuleOrm.id == lesson.module_id)
            .with_for_update(key_share=True)
        )
        if locked is None:
            raise NotFoundError(f"Module {lesson.module_id} does not exist")

        max_order = await self._session.scalar(
            select(func.coalesce(func.max(self.model.order), 0)).where(
                self.model.module_id == lesson.module_id
            )
        )

        target = min(lesson.order, max_order + 1)  # pyright: ignore[reportOptionalOperand]

        await self._session.execute(
            update(self.model)
            .where(self.model.module_id == lesson.module_id, self.model.order >= target)
            .values(order=self.model.order + 1)
            .execution_options(synchronize_session=False)
        )

        lesson.order = target
        return await self.create(lesson)

    async def delete_and_compact(self, lesson_id: UUID) -> None:
        module_id = await self._session.scalar(
            select(self.model.module_id).where(self.model.id == lesson_id)
        )

        if module_id is None:
            if not await self.exists(lesson_id):
                raise NotFoundError(f"Lesson with id {lesson_id} not found")

            await self.delete(lesson_id)
            return

        await self._session.execute(
            select(ModuleOrm.id).where(ModuleOrm.id == module_id).with_for_update(key_share=True)
        )

        lesson_order = await self._session.scalar(
            select(self.model.order)
            .where(
                self.model.id == lesson_id,
                self.model.module_id == module_id,
            )
            .with_for_update(key_share=True)
        )

        if lesson_order is None:
            raise NotFoundError(f"Lesson with id {lesson_id} not found")

        await self.delete(lesson_id)

        await self._session.execute(
            update(self.model)
            .where(
                self.model.module_id == module_id,
                self.model.order > lesson_order,
            )
            .values(order=self.model.order - 1)
        )

    async def get_content_blocks_by_id(self, lesson_id: UUID) -> list[AnyContentBlock] | None:
        """Получает content blocks by id, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model.content_blocks).where(self.model.id == lesson_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def replace_content_block(
        self,
        lesson_id: UUID,
        block_index: int,
        new_block: dict[str, Any],
    ) -> None:
        """Заменяет блок по индексу одним SQL UPDATE, не читая content_blocks в Python."""

        stmt = (
            update(self.model)
            .where(self.model.id == lesson_id)
            .values(
                content_blocks=func.jsonb_set(
                    self.model.content_blocks,
                    text(f"'{{{block_index}}}'"),
                    literal(new_block, type_=JSONB),
                    True,
                )
            )
        )
        await self._session.execute(stmt)

    async def get_by_id_basic_info(self, uid: UUID) -> LessonBasicInfo | None:
        """Получает by id basic info, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(
            self.model.id,
            self.model.title,
            self.model.description,
            self.model.order,
            self.model.learning_objectives,
            self.model.estimated_time_minutes,
        ).where(self.model.id == uid)
        result = await self._session.execute(stmt)
        model = result.one_or_none()
        return None if model is None else self.model_mapper.basic_info_mapper(model)  # type: ignore

    async def assign_module(
        self,
        lesson_id: UUID,
        module_id: UUID,
    ) -> None:
        """Привязывает один урок к модулю и фиксирует это отношение."""
        stmt = update(self.model).where(self.model.id == lesson_id).values(module_id=module_id)

        await self._session.execute(stmt)

    async def read_course_ownership(
        self,
        uid: UUID,
    ) -> tuple[UUID, UUID] | None:
        stmt = (
            select(
                CourseOrm.id.label("course_id"),
                CourseOrm.creator_id,
            )
            .select_from(self.model)
            .join(ModuleOrm, ModuleOrm.id == self.model.module_id)
            .join(CourseOrm, CourseOrm.id == ModuleOrm.course_id)
            .where(self.model.id == uid)
        )

        row = (await self._session.execute(stmt)).one_or_none()

        return (row.course_id, row.creator_id) if row is not None else None
