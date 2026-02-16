from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from tg_bot.core.database import session_factory
from tg_bot.features.course import repository as course_repo

from ... import repository as student_repo
from ...keyboards import CourseMenuAction, CourseMenuCbData
from ...service import get_group_course
from ..ai_agent.utils import ask_edu_assistant
from ..fsm import AIChatState
from ..keyboards import (
    ModuleCbData,
    ModuleMenuAction,
    ModuleMenuCbData,
    get_accessible_modules_kb,
    get_module_menu_kb,
)
from ..lexicon import get_current_module_text, get_module_menu_text
from ..service import get_current_course_progress

router = Router(name=__name__)


@router.callback_query(CourseMenuCbData.filter(F.action == CourseMenuAction.START_STUDYING))
async def cb_start_studying(query: CallbackQuery, callback_data: CourseMenuCbData) -> None:
    await query.answer()
    progress = await get_current_course_progress(
        group_id=callback_data.group_id, user_id=query.from_user.id
    )
    current_module = progress.accessible_modules[-1]
    content = get_current_module_text(
        title=current_module.title,
        description=current_module.description,
        order=current_module.order,
        total=progress.total_modules
    )
    await query.message.answer(
        **content.as_kwargs(), reply_markup=get_accessible_modules_kb(
            group_id=callback_data.group_id, modules=progress.accessible_modules
        )
    )


@router.callback_query(ModuleCbData.filter())
async def cb_module(query: CallbackQuery, callback_data: ModuleCbData) -> None:
    await query.answer()
    course = await get_group_course(callback_data.group_id)
    module = course.modules[callback_data.order]
    async with session_factory() as session:
        student = await student_repo.find_student_in_group(
            session, callback_data.group_id, query.from_user.id)
    content = get_module_menu_text(module.title)
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_module_menu_kb(student.id)
    )


@router.callback_query(ModuleMenuCbData.filter(F.action == ModuleMenuAction.ASK_AI))
async def cb_ask_ai(
        query: CallbackQuery, callback_data: ModuleMenuCbData, state: FSMContext
) -> None:
    await query.answer()
    await query.message.answer("Задайте мне вопрос")
    await state.update_data(student_id=callback_data.student_id)
    await state.set_state(AIChatState.asking_question)


@router.message(AIChatState.asking_question, F.text)
async def process_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    async with session_factory() as session:
        progress = await student_repo.get_student_progress(session, data["student_id"])
        module = await course_repo.get_module(session, progress.current_module_id)
    answer = await ask_edu_assistant(
        module_id=module.id,
        user_id=message.from_user.id,
        question=message.text,
    )
    await message.answer(answer)
    await state.set_state(AIChatState.asking_question)
