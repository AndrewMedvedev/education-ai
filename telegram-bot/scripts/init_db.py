import asyncio
import logging

import anyio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.course import Course
from src.core.entities.student import Group
from src.infra.db.conn import session_factory
from src.infra.db.models import GroupOrm
from src.infra.db.repos import CourseRepository
from src.settings import BASE_DIR

DATA_DIR = BASE_DIR / "data" / "courses"


async def add_group(session: AsyncSession, group: Group) -> None:
    stmt = insert(GroupOrm).values(**group.model_dump())
    await session.execute(stmt)
    await session.commit()


async def main() -> None:
    json_string = await anyio.Path(DATA_DIR / "Инженерия_ПО.json").read_text(encoding="utf-8")
    course = Course.model_validate_json(json_string)
    async with session_factory() as session:
        repo = CourseRepository(session)
        await repo.create(course)
        groups = [
            Group(course_id=course.id, title="АСОиУБ-23-1"),
            Group(course_id=course.id, title="АСОиУБ-23-2")
        ]
        for group in groups:
            await add_group(session, group)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
