from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.core.database import session_factory
from src.features.course import repository as course_repo

from ... import repository as student_repo
from ...keyboards import (
    CourseCbData,
    MenuAction,
    MenuCBData,
    get_course_menu_kb,
    get_list_courses_kb,
)
from ...lexicon import LIST_COURSES_TEXT, get_course_menu_text
from ...service import get_student_courses

router = Router(name=__name__)


@router.callback_query(MenuCBData.filter(F.action == MenuAction.LIST_COURSES))
async def cb_list_courses(query: CallbackQuery) -> None:
    await query.answer()
    courses = await get_student_courses(query.from_user.id)
    await query.message.answer(
        **LIST_COURSES_TEXT.as_kwargs(), reply_markup=get_list_courses_kb(courses)
    )


@router.callback_query(CourseCbData.filter())
async def cb_course(query: CallbackQuery, callback_data: CourseCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        group = await student_repo.find_group_by_course_and_user(
            session, course_id=callback_data.course_id, user_id=query.from_user.id
        )
        course = await course_repo.get(session, group.course_id)
    content = get_course_menu_text(course.title)
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_course_menu_kb(group.id)
    )
