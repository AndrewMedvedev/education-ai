import asyncio
from uuid import UUID

from tg_bot.core.database import session_factory
from tg_bot.features.course import repository as course_repo
from tg_bot.features.course.schemas import Course
from tg_bot.features.student import repository as student_repo


async def get_group_course(group_id: UUID) -> Course | None:
    """Получение текущего курса для группы"""

    async with session_factory() as session:
        group = await student_repo.get_group(session, group_id)
        return await course_repo.get(session, group.course_id)


async def get_user_courses(user_id: int) -> list[Course]:
    """Получение текущих курсов пользователя"""

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


async def get_student_course(student_id: UUID) -> Course:
    """Получение курса студента"""

    async with session_factory() as session:
        student = await student_repo.get_student(session, student_id)
        group = await student_repo.get_group(session, student.group_id)
        return await course_repo.get(session, group.course_id)
