from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.features.user.schemas import UserRole


class RoleSelectionCbData(CallbackData, prefix="role_selection"):
    role: UserRole


def get_role_selection_kb() -> InlineKeyboardMarkup:
    """Inline клавиатура для выбора роли"""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎓 Я преподаватель", callback_data=RoleSelectionCbData(role=UserRole.TEACHER).pack()
    )
    builder.button(
        text="📚 Я студент", callback_data=RoleSelectionCbData(role=UserRole.STUDENT).pack()
    )
    builder.adjust(1)
    return builder.as_markup()
