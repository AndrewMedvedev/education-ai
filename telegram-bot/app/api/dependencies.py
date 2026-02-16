from typing import Annotated

from collections.abc import AsyncIterable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.app.schemas import CurrentUser
from app.infra.db.conn import session_factory
from app.infra.db.repos import CourseRepository
from app.utils.secutiry import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> CurrentUser:
    payload = decode_token(token)
    return CurrentUser.model_validate({
        "user_id": payload["sub"],
        "email": payload["email"],
        "role": payload["role"],
    })


async def get_db() -> AsyncIterable[AsyncSession]:
    async with session_factory() as session:
        yield session


def get_course_repo(session: AsyncSession = Depends(get_db)) -> CourseRepository:
    return CourseRepository(session)
