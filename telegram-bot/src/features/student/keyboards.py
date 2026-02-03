from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MenuAction(StrEnum):
    LIST_COURSES = "list_courses"  # Посмотреть список курсов
    SIGNUP_FOR_COURSE = "signup_for_course"  # Записаться на курс


class MenuCBData(CallbackData, prefix="std_menu"):
    action: MenuAction


def get_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📒 Мои курсы",
        callback_data=MenuCBData(action=MenuAction.LIST_COURSES).pack(),
    )
    builder.button(
        text="🔑 Регистрация на курс",
        callback_data=MenuCBData(action=MenuAction.SIGNUP_FOR_COURSE).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
