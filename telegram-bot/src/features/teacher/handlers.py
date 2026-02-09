from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.formatting import Bold, Italic, Text, as_line, as_marked_section

from src.core.database import session_factory
from src.features.course import repository
from src.features.course.schemas import CourseStatus

from .keyboards import (
    CourseCbData,
    CourseMenuAction,
    CourseMenuCbData,
    MenuAction,
    MenuCBData,
    ModuleCbData,
    get_course_menu_kb,
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
    content = Text(
        Bold("🎓 Список курсов"),
        as_line(),
        as_line("🔢 Общее количество:", f"{len(courses)}"),
        as_line("📢 Опубликовано:", f"{
            len([None for course in courses if course.status == CourseStatus.PUBLISHED])
        }"),
    )
    await query.message.answer(**content.as_kwargs(), reply_markup=get_list_courses_kb(courses))


@router.callback_query(CourseCbData.filter())
async def cb_course(query: CallbackQuery, callback_data: CourseCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        course = await repository.get(session, callback_data.course_id)
    content = Text(
        Bold(f"🎓 {course.title}"),
        as_line(),
        as_line(Bold("📌 Описание")),
        as_line(Italic(f"{course.description}"))
    )
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_course_menu_kb(course.id)
    )


@router.callback_query(CourseMenuCbData.filter(F.action == CourseMenuAction.BACK))
async def cb_back_action(query: CallbackQuery) -> None:
    await query.answer()
    async with session_factory() as session:
        courses = await repository.get_by_creator(session, query.from_user.id)
    content = Text(
        Bold("🎓 Список курсов"),
        as_line("🔢 Общее количество:", f"{len(courses)}"),
        as_line(
            "📢 Опубликовано:",
            f"{len([None for course in courses if course.status == CourseStatus.PUBLISHED])}",
        ),
    )
    await query.message.edit_text(**content.as_kwargs(), reply_markup=get_list_courses_kb(courses))


@router.callback_query(CourseMenuCbData.filter(F.action == CourseMenuAction.VIEW_COURSE))
async def cb_view_course_action(query: CallbackQuery, callback_data: CourseCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        course = await repository.get(session, callback_data.course_id)
    content = Text(
        Bold(f"🎓 {course.title}"),
        as_line(),
        as_line(Bold("📌 Описание")),
        as_line(Italic(f"{course.description}")),
        as_line(),
        as_marked_section(
            Bold("🎯 Цели обучения"), *course.learning_objectives
        )
    )
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_modules_kb(course.modules)
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
        reply_markup=get_module_menu_kb(module.id)
    )
