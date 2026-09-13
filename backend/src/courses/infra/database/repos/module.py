import logging
from uuid import UUID

from sqlalchemy import select, update

from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ....domain.entities import (
    BasicInfo,
    Module,
    ModuleBasicInfo,
)
from ...mappers import (
    ModuleMapper,
)
from ...models import LessonOrm, ModuleOrm

logger = logging.getLogger(__name__)


class SqlModuleRepository(SqlAlchemyRepository[Module, ModuleOrm]):
    model = ModuleOrm
    model_mapper = ModuleMapper  # type: ignore  # ruff:ignore[blanket-type-ignore]

    async def assign_course(
        self,
        module_id: UUID,
        course_id: UUID,
    ) -> None:
        """Связывает курс с родительской сущностью и фиксирует это отношение."""
        stmt = update(self.model).where(self.model.id == module_id).values(course_id=course_id)
        await self._session.execute(stmt)

    async def select_lessons_by_id_module(self, module_id: UUID) -> list[BasicInfo]:
        """Выбирает lessons by id module из хранилища для использования в бизнес-логике."""
        lessons_stmt = (
            select(
                LessonOrm.id,
                LessonOrm.title,
                LessonOrm.order,
            )
            .where(LessonOrm.module_id == module_id)
            .order_by(LessonOrm.order)
        )

        lessons_result = await self._session.execute(lessons_stmt)

        return [
            BasicInfo(
                id=row.id,
                title=row.title,
                order=row.order,
            )
            for row in lessons_result.all()
        ]

    async def get_by_id_basic_info(self, uid: UUID) -> ModuleBasicInfo | None:
        """Получает by id basic info, чтобы вызывающий код работал через единый интерфейс."""
        module_stmt = select(
            self.model.id,
            self.model.title,
            self.model.description,
            self.model.order,
            self.model.learning_objectives,
        ).where(self.model.id == uid)

        module_result = await self._session.execute(module_stmt)
        module_row = module_result.one_or_none()

        if module_row is None:
            return None
        lessons = await self.select_lessons_by_id_module(module_id=uid)

        return self.model_mapper.basic_info_mapper(module_row, lessons)  # type: ignore  # ruff:ignore[blanket-type-ignore]
