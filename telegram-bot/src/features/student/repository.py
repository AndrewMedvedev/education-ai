from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


async def add(session: AsyncSession, student: schemas.Student) -> None:
    """Добавляет студента в текущую сессию"""

    stmt = insert(models.Student).values(**student.model_dump())
    await session.execute(stmt)


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


async def add_group(session: AsyncSession, group: schemas.Group) -> None:
    stmt = insert(models.Group).values(**group.model_dump())
    await session.execute(stmt)


async def get_by_group(session: AsyncSession, group_id: UUID) -> list[schemas.Student]:
    stmt = select(models.Student).where(models.Student.group_id == group_id)
    results = await session.execute(stmt)
    return [
        schemas.Student.model_validate(model) for model in results.scalars().all()
    ]
