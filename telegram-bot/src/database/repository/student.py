from uuid import UUID

from sqlalchemy import func, insert, select
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
