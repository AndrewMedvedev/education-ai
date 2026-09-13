from typing import Any

import logging
from uuid import UUID

from sqlalchemy import func, literal, select, text, update
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ....domain.entities import (
    AnyContentBlock,
    Lesson,
    LessonBasicInfo,
)
from ...mappers import (
    LessonMapper,
)
from ...models import LessonOrm

logger = logging.getLogger(__name__)


class SqlLessonRepository(SqlAlchemyRepository[Lesson, LessonOrm]):
    model = LessonOrm
    model_mapper = LessonMapper  # type: ignore  # ruff:ignore[blanket-type-ignore]

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
        return None if model is None else self.model_mapper.basic_info_mapper(model)  # type: ignore  # ruff:ignore[blanket-type-ignore]

    async def assign_module(
        self,
        lesson_id: UUID,
        module_id: UUID,
    ) -> None:
        """Привязывает один урок к модулю и фиксирует это отношение."""
        stmt = update(self.model).where(self.model.id == lesson_id).values(module_id=module_id)

        await self._session.execute(stmt)
