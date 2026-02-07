import asyncio
import json
import logging

from src.core.database import session_factory
from src.features.course import repository
from src.features.course.schemas import Course

with open("course.json", encoding="utf-8") as file:
    data = json.load(file)

course = Course.model_validate(data)


async def main() -> None:
    async with session_factory() as session:
        """repository.save(session, course)
        await session.commit()"""

        db_course = await repository.get_by_creator(session, 1779915071)
        print(db_course)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
