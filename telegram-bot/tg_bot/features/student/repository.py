from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


async def add_student(session: AsyncSession, student: schemas.Student) -> None:
    """Добавляет студента в текущую сессию"""

    stmt = insert(models.Student).values(**student.model_dump())
    await session.execute(stmt)


async def get_student_by_login(
        session: AsyncSession, student_login: str
) -> schemas.Student | None:
    """Получение студента по его логину"""

    stmt = select(models.Student).where(models.Student.login == student_login)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Student.model_validate(model)


async def activate_student(
        session: AsyncSession, student_id: UUID, user_id: int
) -> schemas.Student:
    """Изменение статуса студента на активный"""

    stmt = (
        update(models.Student)
        .where(models.Student.id == student_id)
        .values(user_id=user_id, is_active=True)
        .returning(models.Student)
    )
    result = await session.execute(stmt)
    model = result.scalar_one()
    return schemas.Student.model_validate(model)


async def add_group(session: AsyncSession, group: schemas.Group) -> None:
    stmt = insert(models.Group).values(**group.model_dump())
    await session.execute(stmt)


async def get_group(session: AsyncSession, group_id: UUID) -> schemas.Group | None:
    stmt = select(models.Group).where(models.Group.id == group_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Group.model_validate(model)


async def get_student(session: AsyncSession, student_id: UUID) -> schemas.Student | None:
    stmt = select(models.Student).where(models.Student.id == student_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Student.model_validate(model)


async def get_students_by_group(session: AsyncSession, group_id: UUID) -> list[schemas.Student]:
    stmt = select(models.Student).where(models.Student.group_id == group_id)
    results = await session.execute(stmt)
    return [
        schemas.Student.model_validate(model) for model in results.scalars().all()
    ]


async def find_student_in_group(
        session: AsyncSession, group_id: UUID, user_id: int
) -> schemas.Student | None:
    stmt = (
        select(models.Student)
        .where(
            (models.Student.group_id == group_id) &
            (models.Student.user_id == user_id)
        )
    )
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Student.model_validate(model)


async def get_students_by_user(session: AsyncSession, user_id: int) -> list[schemas.Student]:
    stmt = select(models.Student).where(models.Student.user_id == user_id)
    results = await session.execute(stmt)
    return [
        schemas.Student.model_validate(model) for model in results.scalars().all()
    ]


async def find_group_by_course_and_user(
        session: AsyncSession, course_id: UUID, user_id: int
) -> schemas.Group | None:
    stmt = (
        select(models.Group)
        .join(models.Student, models.Group.id == models.Student.group_id)
        .where((models.Group.course_id == course_id) & (models.Student.user_id == user_id))
        .order_by(models.Student.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Group.model_validate(model)


async def get_student_progress_in_group(
        session: AsyncSession, group_id: UUID, user_id: int
) -> schemas.StudentProgress | None:
    stmt = (
        select(models.StudentProgress)
        .join(models.Student, models.Student.id == models.StudentProgress.student_id)
        .where(
            (models.Student.group_id == group_id) &
            (models.Student.user_id == user_id)
        )
    )
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.StudentProgress.model_validate(model)


async def get_student_progress(
        session: AsyncSession, student_id: UUID
) -> schemas.StudentProgress | None:
    stmt = select(models.StudentProgress).where(models.StudentProgress.student_id == student_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.StudentProgress.model_validate(model)


async def save_student_progress(session: AsyncSession, progress: schemas.StudentProgress) -> None:
    stmt = insert(models.StudentProgress).values(**progress.model_dump())
    await session.execute(stmt)
