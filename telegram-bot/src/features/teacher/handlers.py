from aiogram import F, Router
from aiogram.types import CallbackQuery

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
from .lexicon import (
    get_course_details_text,
    get_course_list_text,
    get_course_preview_text,
    get_module_preview_text,
)

router = Router(name=__name__)


@router.callback_query(MenuCBData.filter(F.action == MenuAction.LIST_COURSES))
async def cb_list_courses(query: CallbackQuery) -> None:
    await query.answer()
    async with session_factory() as session:
        courses = await repository.get_by_creator(session, query.from_user.id)
    content = get_course_list_text(
        total=len(courses),
        published=len([None for course in courses if course.status == CourseStatus.PUBLISHED])
    )
    await query.message.answer(**content.as_kwargs(), reply_markup=get_list_courses_kb(courses))


@router.callback_query(CourseCbData.filter())
async def cb_course(query: CallbackQuery, callback_data: CourseCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        course = await repository.get(session, callback_data.course_id)
    content = get_course_preview_text(
        title=course.title,
        description=course.description,
        learning_objectives=course.learning_objectives,
    )
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_course_menu_kb(course.id)
    )


@router.callback_query(CourseMenuCbData.filter(F.action == CourseMenuAction.BACK))
async def cb_back_action(query: CallbackQuery) -> None:
    await query.answer()
    async with session_factory() as session:
        courses = await repository.get_by_creator(session, query.from_user.id)
    content = get_course_list_text(
        total=len(courses),
        published=len([None for course in courses if course.status == CourseStatus.PUBLISHED]),
    )
    await query.message.edit_text(**content.as_kwargs(), reply_markup=get_list_courses_kb(courses))


@router.callback_query(CourseMenuCbData.filter(F.action == CourseMenuAction.VIEW_COURSE))
async def cb_view_course_action(query: CallbackQuery, callback_data: CourseCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        course = await repository.get(session, callback_data.course_id)
    content = get_course_details_text(
        title=course.title,
        description=course.description,
        learning_objectives=course.learning_objectives,
        module_titles=[module.title for module in course.modules]
    )
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_modules_kb(course.modules)
    )


@router.callback_query(ModuleCbData.filter())
async def cb_module(query: CallbackQuery, callback_data: ModuleCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        module = await repository.get_module(session, callback_data.module_id)
    content = get_module_preview_text(
        order=module.order,
        title=module.title,
        description=module.description,
    )
    await query.message.answer(
        **content.as_kwargs(), reply_markup=get_module_menu_kb(module.id)
    )
