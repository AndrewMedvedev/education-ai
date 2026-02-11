from uuid import UUID

from src.core.database import session_factory
from src.features.course import repository as course_repo
from src.features.course.schemas import Course
from src.features.student import repository as student_repo


async def get_group_course(group_id: UUID) -> Course | None:
    """Получение текущего курса для группы"""

    async with session_factory() as session:
        group = await student_repo.get_group(session, group_id)
        return await course_repo.get(session, group.course_id)
