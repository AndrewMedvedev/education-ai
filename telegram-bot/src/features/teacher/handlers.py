from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.core.database import session_factory
from src.features.course import repository
from src.features.course.schemas import CourseStatus

from .keyboards import MenuAction, MenuCBData, get_list_courses_kb

router = Router(name=__name__)


@router.callback_query(MenuCBData.filter(F.action == MenuAction.LIST_COURSES))
async def cb_list_courses(query: CallbackQuery) -> None:
    await query.answer()
    async with session_factory() as session:
        courses = await repository.get_by_creator(session, query.from_user.id)
    await query.message.answer(
        text=(
            "<b>📋 Список ваших курсов</b>\n\n"
            f"Количество курсов: {len(courses)}\n"
            f"📢 Опубликовано: {len(
                [None for course in courses if course.status == CourseStatus.PUBLISHED]
            )}"
        ),
        reply_markup=get_list_courses_kb(courses)
    )
