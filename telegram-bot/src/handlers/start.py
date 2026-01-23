from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..keyboards.inline import get_teacher_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.reply(text="Привет", reply_markup=get_teacher_menu_kb())
