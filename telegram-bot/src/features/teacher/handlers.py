from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.core.database import session_factory
from src.features.course import repository
from src.features.course.schemas import CourseStatus

from .keyboards import (
    CourseCbData,
    MenuAction,
    MenuCBData,
    ModuleCbData,
    get_list_courses_kb,
    get_module_menu_kb,
    get_modules_kb,
)

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


@router.callback_query(CourseCbData.filter())
async def cb_course(query: CallbackQuery, callback_data: CourseCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        course = await repository.get(session, callback_data.course_id)
    await query.message.answer(
        text=(
            f"<b>{course.title}</b>\n"
            f"<i>{course.description}</i>\n"
        ),
        reply_markup=get_modules_kb(course.modules)
    )


@router.callback_query(ModuleCbData.filter())
async def cb_module(query: CallbackQuery, callback_data: ModuleCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        module = await repository.get_module(session, callback_data.module_id)
    await query.message.answer(
        text=(
            f"<b>{module.title}</b>"
            f"<i>{module.description}</i>"
        ),
        reply_markup=get_module_menu_kb(module)
    )
