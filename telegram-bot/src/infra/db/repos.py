from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.entities.course import Course, Module
from ...core.entities.student import Group, LearningProgress
from ...core.entities.user import AnyUser, Student, Teacher
from .base import Base
from .models import (
    AnyUserOrm,
    CourseOrm,
    GroupOrm,
    LearningProgressOrm,
    ModuleOrm,
    StudentOrm,
    TeacherOrm,
    UserOrm,
)


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


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_orm(user: AnyUser) -> AnyUserOrm:
        if isinstance(user, Student):
            return StudentOrm(**user.model_dump())
        if isinstance(user, Teacher):
            return TeacherOrm(**user.model_dump())
        raise ValueError("Unexpected user instance!")

    @staticmethod
    def _from_orm(model: AnyUserOrm) -> AnyUser:
        if isinstance(model, StudentOrm):
            return Student.model_validate(model)
        if isinstance(model, TeacherOrm):
            return Teacher.model_validate(model)
        raise ValueError("Unexpected model instance!")

    async def create(self, user: AnyUser) -> None:
        model = self._to_orm(user)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

    async def read(self, user_id: int) -> AnyUser:
        stmt = select(UserOrm).where(UserOrm.id == user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self._from_orm(model)


class StudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_groups(self) -> list[Group]:
        stmt = select(GroupOrm)
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [Group.model_validate(model) for model in models]

    async def get_student_group(self, student_id: int) -> Group | None:
        stmt = (
            select(GroupOrm)
            .join(StudentOrm, StudentOrm.group_id == GroupOrm.id)
            .where(StudentOrm.id == student_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else Group.model_validate(model)

    async def save_learning_progress(self, progress: LearningProgress) -> None:
        stmt = insert(LearningProgressOrm).values(**progress.model_dump())
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_learning_progress(self, student_id: int) -> LearningProgress | None:
        stmt = select(LearningProgressOrm).where(LearningProgressOrm.student_id == student_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else LearningProgress.model_validate(model)

    async def update_learning_progress(self, student_id: int, **kwargs) -> LearningProgress:
        stmt = (
            update(LearningProgressOrm)
            .where(LearningProgressOrm.student_id == student_id)
            .values(**kwargs)
            .returning(LearningProgressOrm)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        model = result.scalar_one()
        return LearningProgress.model_validate(model)


class CourseRepository(SqlAlchemyRepository[Course, CourseOrm]):
    entity = Course
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
                    learning_objectives=module.learning_objectives,
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

    async def refresh(self, course: Course) -> None:
        model = self._to_orm(course)
        await self.session.merge(model)
        await self.session.commit()
        await self.session.refresh(model)

    async def get_module(self, module_id: UUID) -> Module | None:
        stmt = select(ModuleOrm).where(ModuleOrm.id == module_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else Module.model_validate(model)
