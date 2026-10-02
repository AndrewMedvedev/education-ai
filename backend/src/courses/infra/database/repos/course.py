import logging
from uuid import UUID

from sqlalchemy import select

from src.shared.application.dtos import Page, Pagination
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository, paginate

from ....domain.entities import (
    BasicInfo,
    Course,
    CourseBasicInfo,
)
from ....domain.vo import CourseStatus
from ..mappers import (
    CourseMapper,
)
from ..models import CourseOrm, MemberOrm, ModuleOrm

logger = logging.getLogger(__name__)


class SqlCourseRepository(SqlAlchemyRepository[Course, CourseOrm]):
    model = CourseOrm
    model_mapper = CourseMapper  # type: ignore

    async def find(
        self,
        pagination: Pagination,
    ) -> Page[Course]:
        """Для расширения логики фильтрации можно переопределить в дочерних классах."""

        stmt = (
            select(self.model)
            .order_by(self.model.created_at.desc())
            .where(self.model.status == CourseStatus.PUBLISHED)
        )

        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,
            pagination=pagination,
            mapper=self.model_mapper.from_model,
        )

    async def find_user_courses(
        self,
        user_id: UUID,
        pagination: Pagination,
    ) -> Page[Course]:
        """Для расширения логики фильтрации можно переопределить в дочерних классах."""

        stmt = (
            select(self.model)
            .order_by(self.model.created_at.desc())
            .where(self.model.creator_id == user_id)
        )

        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,
            pagination=pagination,
            mapper=self.model_mapper.from_model,
        )

    async def find_member_courses(
        self,
        user_id: UUID,
        pagination: Pagination,
    ) -> Page[Course]:
        """Получает курсы, на которые записан студент."""

        stmt = (
            select(self.model)
            .join(
                MemberOrm,
                MemberOrm.course_id == self.model.id,
            )
            .where(
                MemberOrm.user_id == user_id,
                self.model.status.notin_(
                    [
                        CourseStatus.ARCHIVED,
                        CourseStatus.DRAFT,
                    ]
                ),
            )
        )

        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,
            pagination=pagination,
            mapper=self.model_mapper.from_model,
            sort="created_at:desc",
        )

    async def select_modules_by_id_course(self, course_id: UUID) -> list[BasicInfo]:
        """Выбирает modules by id course из хранилища для использования в бизнес-логике."""
        modules_stmt = (
            select(
                ModuleOrm.id,
                ModuleOrm.title,
                ModuleOrm.order,
            )
            .where(ModuleOrm.course_id == course_id)
            .order_by(ModuleOrm.order)
        )
        modules_result = await self._session.execute(modules_stmt)

        return [
            BasicInfo(
                id=row.id,
                title=row.title,
                order=row.order,
            )
            for row in modules_result.all()
        ]

    async def get_by_id_basic_info(self, uid: UUID) -> CourseBasicInfo | None:
        """Получает by id basic info, чтобы вызывающий код работал через единый интерфейс."""
        course_stmt = select(
            self.model.id,
            self.model.title,
            self.model.description,
            self.model.difficulty,
            self.model.tags,
            self.model.learning_objectives,
        ).where(self.model.id == uid)

        course_result = await self._session.execute(course_stmt)
        course_row = course_result.one_or_none()

        if course_row is None:
            return None

        modules = await self.select_modules_by_id_course(uid)

        return self.model_mapper.basic_info_mapper(course_row, modules)  # type: ignore

    async def get_course_status(
        self,
        course_id: UUID,
        user_id: UUID,
    ) -> CourseStatus | None:
        """Получает статус курса по его идентификатору."""
        stmt = select(self.model.status).where(
            self.model.id == course_id,
            self.model.creator_id == user_id,
        )

        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    async def find_members(
        self,
        course_id: UUID,
        pagination: Pagination,
    ) -> Page[Course]:
        """Для расширения логики фильтрации можно переопределить в дочерних классах."""

        stmt = (
            select(self.model.members)
            .order_by(self.model.created_at.desc())
            .where(self.model.id == course_id)
        )

        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,  # pyright: ignore[reportArgumentType]
            pagination=pagination,
            mapper=self.model_mapper.from_model,
        )

    async def read_creator_id(self, course_id: UUID) -> UUID | None:
        """Получает существующую запись по идентификатору или заданным параметрам."""
        stmt = select(self.model.creator_id).where(self.model.id == course_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
