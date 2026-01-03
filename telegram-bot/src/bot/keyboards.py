from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..settings import settings


def start_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Создать курс", web_app=WebAppInfo(url=f"{settings.ngrok.url}/courses/create")
    )
    return builder.as_markup()
