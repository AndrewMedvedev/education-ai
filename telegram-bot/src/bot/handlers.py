from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from .keyboards import start_kb

router = Router(name=__name__)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.reply(
        "Привет! Давай создадим курс",
        reply_markup=start_kb()
    )
