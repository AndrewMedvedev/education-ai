from collections.abc import AsyncIterable

from fastapi import Body, Depends, HTTPException, status
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services import check_daily_chat_limit
from src.infra.db.conn import session_factory
from src.infra.db.repos import CourseRepository


async def get_db() -> AsyncIterable[AsyncSession]:
    async with session_factory() as session:
        yield session


def get_course_repo(session: AsyncSession = Depends(get_db)) -> CourseRepository:
    return CourseRepository(session)


async def enforce_daily_chat_limit(
    user_id: PositiveInt = Body(..., embed=True, description="ID студента")
) -> None:
    allowed = await check_daily_chat_limit(user_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The daily chat limit has been reached (10 messages / day)!",
            headers={"Retry-After": "86400"},
        )
