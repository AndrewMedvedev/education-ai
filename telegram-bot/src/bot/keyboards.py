from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import StartCBData


def start_kb(tg_user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Создать курс", callback_data=StartCBData(tg_user_id=tg_user_id).pack())
    return builder.as_markup()
