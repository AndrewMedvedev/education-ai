from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import BlockQuote, Bold, Text, as_line

from src.core.commons import current_datetime
from src.core.entities.student import LearningProgress
from src.infra.db.conn import session_factory
from src.infra.db.repos import CourseRepository, StudentRepository

from ..keyboards import (
    ModuleAction,
    ModuleCbData,
    ModuleStudyCbData,
    get_module_study_kb,
    get_modules_kb,
)

router = Router(name=__name__)


@router.message(Command("study"))
async def cmd_study(message: Message, state: FSMContext) -> None:
    """Начать или продолжить обучение"""

    student_id = message.from_user.id
    async with session_factory() as session:
        student_repo = StudentRepository(session)
        course_repo = CourseRepository(session)
        group = await student_repo.get_student_group(student_id)
        course = await course_repo.read(group.course_id)
        learn_progress = await student_repo.get_learning_progress(student_id)
        if learn_progress is None:
            fist_module = course.modules[0]
            learn_progress = LearningProgress(
                student_id=student_id,
                course_id=group.course_id,
                started_at=current_datetime(),
                current_module_id=fist_module.id,
            )
            await student_repo.save_learning_progress(learn_progress)
    current_module_order = next(
        (
            order
            for order, module in enumerate(course.modules)
            if module.id == learn_progress.current_module_id
        ),
        None,
    )
    await state.update_data(
        group_id=group.id,
        course_id=group.course_id,
        current_module_id=learn_progress.current_module_id,
        module_order=current_module_order,
    )
    await message.answer(
        **Text(
            as_line(Bold(f"🎓 {course.title}"), end="\n\n"),
            as_line(BlockQuote(course.description)),
        ).as_kwargs(),
        reply_markup=get_modules_kb(
            modules=course.modules, current_module_id=learn_progress.current_module_id
        ),
    )


@router.callback_query(ModuleCbData.filter())
async def cb_module(query: CallbackQuery, callback_data: ModuleCbData, state: FSMContext) -> None:
    """Прохождение модуля"""

    await query.answer()
    data = await state.get_data()
    async with session_factory() as session:
        course_repo = CourseRepository(session)
        module = await course_repo.get_module(callback_data.module_id)
        if module.order > data["module_order"]:
            await query.answer(text="Материал недоступен!", show_alert=True)
            return
    await query.message.edit_text(
        **Text(
            as_line(Bold(f"📚 {module.title}"), end="\n\n"),
            as_line(BlockQuote(module.description)),
        ).as_kwargs(),
        reply_markup=get_module_study_kb(),
    )
