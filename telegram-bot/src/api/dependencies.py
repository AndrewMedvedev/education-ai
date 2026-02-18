from collections.abc import AsyncIterable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.conn import session_factory
from src.infra.db.repos import CourseRepository


async def get_db() -> AsyncIterable[AsyncSession]:
    async with session_factory() as session:
        yield session


def get_course_repo(session: AsyncSession = Depends(get_db)) -> CourseRepository:
    return CourseRepository(session)
