from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class TeacherMenuAction(StrEnum):
    LIST_COURSES = "list_courses"
    CREATE_COURSE = "create_course"


class TeacherMenuCBData(CallbackData, prefix="tchr_menu"):
    action: TeacherMenuAction


def get_teacher_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📒 Мои курсы",
        callback_data=TeacherMenuCBData(action=TeacherMenuAction.LIST_COURSES).pack(),
    )
    builder.button(
        text="➕ Создать курс",
        callback_data=TeacherMenuCBData(action=TeacherMenuAction.CREATE_COURSE).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
