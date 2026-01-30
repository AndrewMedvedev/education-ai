from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    from src.features.teacher.keyboards import get_teacher_menu_kb  # noqa: PLC0415

    await message.reply(text="Привет", reply_markup=get_teacher_menu_kb())
