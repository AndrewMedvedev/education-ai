from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from .callbacks import StartCBData
from .keyboards import start_kb

router = Router(name=__name__)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.reply("Привет!", reply_markup=start_kb(tg_user_id=message.from_user.id))


@router.callback_query(StartCBData.filter())
async def handle_start_cb(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.edit_text(
        text="""Отлично, давайте создадим курс. Отправьте ваши учебные материалы."""
    )


@router.message(F.document)
async def download_education_materials_media(
        message: Message, album_messages: list[Message] | None = None
) -> None:
    if album_messages is None:
        text = f"Got document <b>{message.document.file_name}</b>"
        await message.answer(text=text)
        return
