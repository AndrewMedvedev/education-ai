from typing import Literal

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class SignupConfirmCbData(CallbackData, prefix="std_signup_confirm"):
    action: Literal["cancel", "enter"]


def get_signup_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✔️ Войти", callback_data=SignupConfirmCbData(action="enter").pack(),
    )
    builder.button(
        text="❌ Отмена", callback_data=SignupConfirmCbData(action="cancel").pack()
    )
    return builder.as_markup()
