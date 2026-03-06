from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name=__name__)


@router.message(Command("info"))
async def cmd_info(message: Message) -> None:
    """Информация о боте, инструкции"""

    await message.answer(text=".")


@router.message(Command("support"))
async def cmd_support(message: Message) -> None:
    """Получение контактов тех поддержки"""

    await message.answer(
        text=(
            "<b>Разработчики:</b> @Andr17k @andremedvdv\n\n"
            "<i>❗Если вы нашли баг или хотите оставить обратную связь</i>"
        )
    )
