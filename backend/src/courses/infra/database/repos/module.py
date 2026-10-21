import logging
from uuid import UUID

from sqlalchemy import func, select, update

from src.courses.application.dtos import (
    BasicInfo,
    ModuleBasicInfo,
)
from src.courses.domain.entities import Module
from src.shared.domain.exceptions import NotFoundError
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ..mappers import (
    ModuleMapper,
)
from ..models import CourseOrm, LessonOrm, ModuleOrm

logger = logging.getLogger(__name__)


class SqlModuleRepository(SqlAlchemyRepository[Module, ModuleOrm]):
    model = ModuleOrm
    model_mapper = ModuleMapper  # type: ignore

    async def create_at(self, module: Module) -> Module:
        if module.order < 0:
            raise ValueError("Module order must be non-negative")

        if module.course_id is None:
            raise ValueError("course_id is required")

        locked = await self._session.scalar(
            select(CourseOrm.id)
            .where(CourseOrm.id == module.course_id)
            .with_for_update(key_share=True)
        )
        if locked is None:
            raise NotFoundError(f"Course {module.course_id} does not exist")

        max_order = await self._session.scalar(
            select(func.coalesce(func.max(self.model.order), 0)).where(
                self.model.course_id == module.course_id
            )
        )

        target = min(module.order, max_order + 1)  # pyright: ignore[reportOptionalOperand]

        await self._session.execute(
            update(self.model)
            .where(
                self.model.course_id == module.course_id,
                self.model.order >= target,
            )
            .values(order=self.model.order + 1)
            .execution_options(synchronize_session=False)
        )

        module.order = target
        return await self.create(module)

    async def delete_and_compact(self, module_id: UUID) -> None:
        course_id = await self._session.scalar(
            select(self.model.course_id).where(self.model.id == module_id)
        )
        if course_id is None:
            exists = await self.exists(module_id)

            if not exists:
                raise NotFoundError(f"Module with id {module_id} not found")

            # Модуль существует, но не привязан к курсу.
            # Уплотнять порядок нечего.
            await self.delete(module_id)
            return

        await self._session.execute(
            select(CourseOrm.id).where(CourseOrm.id == course_id).with_for_update(key_share=True)
        )

        module_row = (
            await self._session.execute(
                select(self.model.order)
                .where(
                    self.model.id == module_id,
                    self.model.course_id == course_id,
                )
                .with_for_update(key_share=True)
            )
        ).one_or_none()

        if module_row is None:
            raise NotFoundError(f"Module with id {module_id} not found")

        await self.delete(module_id)

        await self._session.execute(
            update(self.model)
            .where(
                self.model.course_id == course_id,
                self.model.order > module_row.order,
            )
            .values(order=self.model.order - 1)
        )

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

        return self.model_mapper.basic_info_mapper(module_row, lessons)  # type: ignore

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
            .join(CourseOrm, CourseOrm.id == self.model.course_id)
            .where(self.model.id == uid)
        )

        row = (await self._session.execute(stmt)).one_or_none()

        return (row.course_id, row.creator_id) if row is not None else None
