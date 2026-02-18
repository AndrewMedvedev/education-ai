from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.core.entities.user import AnyUser, UserRole
from src.infra.db.conn import session_factory
from src.infra.db.repos import UserRepository

from ..keyboards import get_role_choice_kb
from ..lexicon import STUDENT_CMD_MENU_TEXT

router = Router(name=__name__)


async def handle_any_user(message: Message, user: AnyUser):
    match user.role:
        case UserRole.STUDENT:
            await message.answer(**STUDENT_CMD_MENU_TEXT.as_kwargs())
        case UserRole.TEACHER:
            await message.answer(text="...")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.read(message.from_user.id)
        if user is None:
            await message.answer(text="Выберите роль", reply_markup=get_role_choice_kb())
            return
        await handle_any_user(message, user)
