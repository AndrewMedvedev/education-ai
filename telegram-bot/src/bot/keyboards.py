from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.entities.user import UserRole


class UserChoiceCbData(CallbackData, prefix="role_selection"):
    role: UserRole


def get_role_choice_kb() -> InlineKeyboardMarkup:
    """Inline клавиатура для выбора роли"""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🧑🏻‍🎓 Студент", callback_data=UserChoiceCbData(role=UserRole.STUDENT).pack()
    )
    builder.button(
        text="🧑🏻‍🏫 Преподаватель", callback_data=UserChoiceCbData(role=UserRole.TEACHER).pack()
    )
    builder.adjust(1)
    return builder.as_markup()


def get_group_choice_kb() -> InlineKeyboardMarkup:
    ...
