from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.course import Course, Module
from app.core.entities.student import IndividualAssignment, Student
from app.core.entities.user import User

from .models.base import Base
from .models.course import CourseOrm, ModuleOrm
from .models.student import IndividualAssignmentOrm, StudentOrm
from .models.user import UserOrm


class SqlAlchemyRepository[EntityT: BaseModel, ModelT: Base]:
    entity: type[EntityT]
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: EntityT) -> None:
        stmt = insert(self.model).values(**entity.model_dump())
        await self.session.execute(stmt)
        await self.session.flush()
        await self.session.commit()

    async def read(self, id: UUID) -> EntityT | None:  # noqa: A002
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)

    async def update(self, id: UUID, **kwargs) -> EntityT | None:  # noqa: A002
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        await self.session.commit()
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)

    async def delete(self, id: UUID) -> None:  # noqa: A002
        stmt = delete(self.model).where(self.model.id == id)
        await self.session.execute(stmt)
        await self.session.commit()


class UserRepository(SqlAlchemyRepository[User, UserOrm]):
    entity = User
    model = UserOrm

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(self.model).where(self.model.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)


class CourseRepository(SqlAlchemyRepository[Course, CourseOrm]):
    schema = Course
    model = CourseOrm

    @staticmethod
    def _to_orm(course: Course) -> CourseOrm:
        """Маппинг сущности к ORM модели"""

        return CourseOrm(
            id=course.id,
            created_at=course.created_at,
            creator_id=course.creator_id,
            status=course.status,
            image_url=course.image_url,
            title=course.title,
            description=course.description,
            learning_objectives=course.learning_objectives,
            modules=[
                ModuleOrm(
                    id=module.id,
                    course_id=course.id,
                    order=module.order,
                    title=module.title,
                    description=module.description,
                    content_blocks=[
                        content_block.model_dump() for content_block in module.content_blocks
                    ],
                    assignment=(
                        module.assignment.model_dump() if module.assignment is not None else None
                    ),
                )
                for module in course.modules
            ],
            final_assessment=(
                None if course.final_assessment is None else course.final_assessment.model_dump()
            ),
        )

    async def create(self, course: Course) -> None:
        model = self._to_orm(course)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

    async def get_module(self, module_id: UUID) -> Module | None:
        stmt = select(ModuleOrm).where(ModuleOrm.id == module_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else Module.model_validate(model)


class StudentRepository(SqlAlchemyRepository[Student, StudentOrm]):
    schema = Student
    model = StudentOrm

    async def add_individual_assignment(self, assignment: IndividualAssignment) -> None:
        stmt = insert(IndividualAssignmentOrm).values(**assignment.model_dump())
        await self.session.execute(stmt)
        await self.session.commit()
