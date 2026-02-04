from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.features.course.schemas import Course


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


class CourseCbData(CallbackData, prefix="tchr_course"):
    course_id: UUID


def get_list_courses_kb(courses: list[Course]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.button(
            text=course.title, callback_data=CourseCbData(course_id=course.id).pack()
        )
    builder.adjust(1)
    return builder.as_markup()
