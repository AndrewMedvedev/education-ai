from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.infra.db.conn import session_factory
from src.infra.db.repos import CourseRepository, StudentRepository

from ..lexicon import STUDENT_PROFILE_TEMPLATE

router = Router(name=__name__)


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    """Профиль студента"""

    async with session_factory() as session:
        student_repo = StudentRepository(session)
        course_repo = CourseRepository(session)
        student = await student_repo.read(message.from_user.id)
        groups = await student_repo.get_groups()
        group = next((group for group in groups if group.id == student.group_id), None)
        progress = await student_repo.get_learning_progress(student.id)
        if progress is None:
            await message.answer(
                STUDENT_PROFILE_TEMPLATE.format(
                    user_mention=message.from_user.mention_html(),
                    full_name=student.full_name,
                    group=group.title,
                    total_score=0,
                    learning_percent=0,
                )
            )
            return
        course = await course_repo.read(group.course_id)
    module_order = next(
        (module.order for module in course.modules if module.id == progress.current_module_id),
        None
    )
    learning_percent = round(((module_order + 1) / len(course.modules)) * 100, 2)
    await message.answer(
        STUDENT_PROFILE_TEMPLATE.format(
            user_mention=message.from_user.mention_html(),
            full_name=student.full_name,
            group=group.title,
            total_score=progress.total_score,
            learning_percent=learning_percent,
        )
    )
    await state.update_data(
        group_id=group.id,
        course_id=course.id,
        module_id=progress.current_module_id,
        module_order=module_order,
    )
