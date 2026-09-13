from typing import Any

import logging
from uuid import UUID

from sqlalchemy import select

from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ....domain.entities import (
    Practice,
)
from ...mappers import (
    PracticeMapper,
)
from ...models import PracticeOrm

logger = logging.getLogger(__name__)


class SqlPracticeRepository(SqlAlchemyRepository[Practice, PracticeOrm]):
    model = PracticeOrm
    model_mapper = PracticeMapper  # pyright: ignore[reportAssignmentType]

    async def read(self, user_id: UUID, module_id: UUID, lesson_id: UUID) -> Practice | None:
        """Получает существующую запись по идентификатору или заданным параметрам."""
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.module_id == module_id,
            self.model.lesson_id == lesson_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def read_by_module(self, user_id: UUID, module_id: UUID) -> list[dict[str, Any]]:
        """Получает практики пользователя внутри модуля без служебных полей."""
        stmt = (
            select(
                self.model.practice,
                self.model.status,
            )
            .where(
                self.model.user_id == user_id,
                self.model.module_id == module_id,
            )
            .order_by(self.model.lesson_id)
        )

        result = await self._session.execute(stmt)

        return [
            {
                "practice": row.practice,
                "status": row.status,
            }
            for row in result.all()
        ]
