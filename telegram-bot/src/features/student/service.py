import asyncio
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


async def get_student_courses(user_id: int) -> list[Course]:
    """Получение текущих курсов студента"""

    async with session_factory() as session:
        students = await student_repo.get_students_by_user(session, user_id)

        async def fetch_course(group_id: UUID) -> Course | None:
            group = await student_repo.get_group(session, group_id)
            return await course_repo.get(session, group.course_id)

        tasks = [fetch_course(student.group_id) for student in students]
        courses = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        course for course in courses
        if course is not None and not isinstance(course, Exception)
    ]
