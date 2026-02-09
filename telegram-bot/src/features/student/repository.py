from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


def add(session: AsyncSession, student: schemas.Student) -> None:
    """Добавляет студента в текущую сессию"""

    model = models.Student(**student.model_dump())
    session.add(model)


async def get_count_on_course(session: AsyncSession, course_id: UUID) -> int:
    """Получает количество студентов на курсе"""

    stmt = (
        select(func.count())
        .select_from(models.Student)
        .where(models.Student.course_id == course_id)
    )
    result = await session.execute(stmt)
    return result.scalar()


async def get_by_login(session: AsyncSession, student_login: str) -> schemas.Student | None:
    """Получение студента по его логину"""

    stmt = select(models.Student).where(models.Student.login == student_login)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Student.model_validate(model)


async def activate(session: AsyncSession, student_id: UUID) -> schemas.Student:
    """Изменение статуса студента на активный"""

    stmt = update(models.Student).where(models.Student.id == student_id).values(is_active=True)
    result = await session.execute(stmt)
    model = result.scalar_one()
    return schemas.Student.model_validate(model)
