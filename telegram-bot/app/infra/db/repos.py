from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.course import Course, Module
from app.core.entities.student import IndividualAssignment, Student

from .models.base import Base
from .models.course import CourseOrm, ModuleOrm
from .models.student import IndividualAssignmentOrm, StudentOrm


class SqlAlchemyRepository[SchemaT: BaseModel, ModelT: Base]:
    schema: type[SchemaT]
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, schema: SchemaT) -> None:
        stmt = insert(self.model).values(**schema.model_dump())
        await self.session.execute(stmt)
        await self.session.flush()
        await self.session.commit()

    async def read(self, id: UUID) -> SchemaT | None:  # noqa: A002
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.schema.model_validate(model)

    async def update(self, id: UUID, **kwargs) -> SchemaT | None:  # noqa: A002
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
        return None if model is None else self.schema.model_validate(model)

    async def delete(self, id: UUID) -> None:  # noqa: A002
        stmt = delete(self.model).where(self.model.id == id)
        await self.session.execute(stmt)
        await self.session.commit()


class CourseRepository(SqlAlchemyRepository[Course, CourseOrm]):
    schema = Course
    model = CourseOrm


class ModuleRepository(SqlAlchemyRepository[Module, ModuleOrm]):
    schema = Module
    model = ModuleOrm


class StudentRepository(SqlAlchemyRepository[Student, StudentOrm]):
    schema = Student
    model = StudentOrm

    async def add_individual_assignment(self, assignment: IndividualAssignment) -> None:
        stmt = insert(IndividualAssignmentOrm).values(**assignment.model_dump())
        await self.session.execute(stmt)
        await self.session.commit()
