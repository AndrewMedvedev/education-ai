from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core import schemas
from .. import models


async def get_count(session: AsyncSession, course_id: UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(models.Student)
        .where(models.Student.course_id == course_id)
    )
    result = await session.execute(stmt)
    return result.scalar()


async def save(session: AsyncSession, student: schemas.Student) -> None:
    stmt = insert(models.Student).values(**student.model_dump())
    await session.execute(stmt)


async def read(session: AsyncSession, user_id: int) -> schemas.Student | None:
    stmt = select(models.Student).where(models.Student.user_id == user_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Student.model_validate(model)


async def get_by_login(session: AsyncSession, login: str) -> schemas.Student | None:
    stmt = select(models.Student).where(models.Student.login == login)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Student.model_validate(model)


async def activate(session: AsyncSession, user_id: int) -> schemas.Student:
    stmt = (
        update(models.Student)
        .where(models.Student.user_id == user_id)
        .values(user_id=user_id, is_active=True)
        .returning(models.Student)
    )
    result = await session.execute(stmt)
    model = result.scalar_one()
    return schemas.Student.model_validate(model)
