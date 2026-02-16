from uuid import UUID

from tg_bot.core.database import session_factory
from tg_bot.features.course import repository as course_repo
from tg_bot.utils import current_datetime

from .. import repository as student_repo
from ..schemas import CourseProgress, StudentProgress


async def get_current_course_progress(group_id: UUID, user_id: int) -> CourseProgress:
    """Получение доступных модулей для студента, учитывая его прогресс обучения"""

    async with session_factory() as session:
        student = await student_repo.find_student_in_group(session, group_id, user_id)
        progress = await student_repo.get_student_progress(session, student.id)
        group = await student_repo.get_group(session, group_id)
        course = await course_repo.get(session, group.course_id)
        if progress is None:
            first_module = course.modules[0]
            progress = StudentProgress(
                student_id=student.id,
                started_at=current_datetime(),
                current_module_id=first_module.id,
            )
            await student_repo.save_student_progress(session, progress)
            await session.commit()
            return CourseProgress(
                student_id=student.id,
                current_module_id=first_module.id,
                total_modules=len(course.modules),
                accessible_modules=[first_module],
            )
        current_module = next(
            (
                module for module in course.modules
                if module.id == progress.current_module_id), None
        )
        return CourseProgress(
            student_id=student.id,
            current_module_id=current_module.id,
            total_modules=len(course.modules),
            accessible_modules=[
                module for module in course.modules
                if module.order <= current_module.order
            ],
        )
