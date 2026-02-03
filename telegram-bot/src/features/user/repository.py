from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


def save(session: AsyncSession, user: schemas.User) -> None:
    """Сохраняет пользователя в текущей сессии"""

    model = models.User(**user.model_dump())
    session.add(model)


async def get(session: AsyncSession, user_id: int) -> schemas.User | None:
    stmt = select(models.User).where(models.User.id == user_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.User.model_validate(model)
