from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.formatting import Bold, BotCommand, Text, as_line, as_marked_section

from src.core.entities.user import AnyUser, UserRole
from src.infra.db.conn import session_factory
from src.infra.db.repos import UserRepository

from ..keyboards import get_role_choice_kb

router = Router(name=__name__)


async def handle_any_user(message: Message, user: AnyUser):
    match user.role:
        case UserRole.STUDENT:
            content = Text(
                as_marked_section(
                    Bold("⚙️ Командное меню:"),
                    as_line(BotCommand("study"), " - прохождение курса"),
                )
            )
            await message.answer(**content)
        case UserRole.TEACHER:
            await message.answer(...)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.read(message.from_user.id)
        if user is None:
            await message.answer(text="", reply_markup=get_role_choice_kb())
            return
        await handle_any_user(message, user)
