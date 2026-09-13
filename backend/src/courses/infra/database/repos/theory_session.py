import logging
from uuid import UUID

from sqlalchemy import select

from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository, apply_sorting

from ....application.dtos import LessonTheorySessionFilters
from ....domain.entities import (
    LessonTheorySession,
)
from ...mappers import LessonTheorySessionMapper
from ...models import LessonTheorySessionOrm

logger = logging.getLogger(__name__)


class SqlLessonTheorySessionRepository(
    SqlAlchemyRepository[LessonTheorySession, LessonTheorySessionOrm]
):
    model = LessonTheorySessionOrm
    model_mapper = LessonTheorySessionMapper  # pyright: ignore[reportAssignmentType]

    async def find(
        self,
        *,
        lesson_id: UUID,
        user_id: UUID,
        filters: LessonTheorySessionFilters | None = None,
    ) -> list[LessonTheorySession]:
        stmt = select(self.model).where(
            self.model.lesson_id == lesson_id,
            self.model.user_id == user_id,
        )

        if filters:
            if filters.created_from:
                stmt = stmt.where(
                    self.model.created_at >= filters.created_from,
                )

            if filters.created_to:
                stmt = stmt.where(
                    self.model.created_at < filters.created_to,
                )

        stmt = apply_sorting(
            stmt,
            self.model,
            filters.sort if filters else None,
        )

        result = await self._session.execute(stmt)

        return [self.model_mapper.from_model(model) for model in result.scalars().all()]
