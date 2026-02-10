from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.config import settings
from src.features.course.schemas import Course, Module


class MenuAction(StrEnum):
    LIST_COURSES = "list_courses"
    CREATE_COURSE = "create_course"


class MenuCBData(CallbackData, prefix="tchr_menu"):
    action: MenuAction


def get_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📒 Мои курсы",
        callback_data=MenuCBData(action=MenuAction.LIST_COURSES).pack(),
    )
    builder.button(
        text="➕ Создать курс",
        callback_data=MenuCBData(action=MenuAction.CREATE_COURSE).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


class CourseCbData(CallbackData, prefix="tchr_crs"):
    course_id: UUID


def get_list_courses_kb(courses: list[Course]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.button(
            text=course.title, callback_data=CourseCbData(course_id=course.id).pack()
        )
    builder.adjust(1)
    return builder.as_markup()


class ModuleCbData(CallbackData, prefix="tchr_mdl"):
    module_id: UUID


def get_modules_kb(modules: list[Module]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for module in modules:
        builder.button(
            text=module.title, callback_data=ModuleCbData(module_id=module.id).pack()
        )
    builder.adjust(1)
    return builder.as_markup()


class ModuleSection(StrEnum):
    THEORY = "theory"
    PRACTICE = "practice"


class ModuleMenuCbData(CallbackData, prefix="tchr_mdl_menu"):
    module_id: UUID
    section: ModuleSection


def get_module_menu_kb(module_id: UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📖 Теоретический материал", web_app=WebAppInfo(
            url=f"{settings.app.url}/teacher/courses/modules/{module_id}/theory"
        )
    )
    builder.button(
        text="🎯 Практическое задание", web_app=WebAppInfo(
            url=f"{settings.app.url}/teacher/courses/modules/{module_id}/practice"
        )
    )
    builder.adjust(1)
    return builder.as_markup()


class CourseMenuAction(StrEnum):
    INVITE_STUDENTS = "invite_students"  # Пригласить студентов
    DASHBOARDS = "dashboards"  # Админ панель
    VIEW_COURSE = "view_course"  # Просмотр курса
    BACK = "back"


class CourseMenuCbData(CallbackData, prefix="tchr_crs_menu"):
    course_id: UUID
    action: CourseMenuAction


def get_course_menu_kb(course_id: UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📨 Пригласить студентов", callback_data=CourseMenuCbData(
            course_id=course_id, action=CourseMenuAction.INVITE_STUDENTS
        )
    )
    builder.button(
        text="📊 Админ панель", web_app=WebAppInfo(
            url=f"{settings.app.url}/teacher/courses/{course_id}/dashboards"
        )
    )
    builder.button(
        text="🗂️ Просмотр содержания", callback_data=CourseMenuCbData(
            course_id=course_id, action=CourseMenuAction.VIEW_COURSE
        )
    )
    builder.button(
        text="🔙 Назад", callback_data=CourseMenuCbData(
            course_id=course_id, action=CourseMenuAction.BACK
        )
    )
    builder.adjust(1)
    return builder.as_markup()
