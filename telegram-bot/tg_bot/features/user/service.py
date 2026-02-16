from aiogram.types import CallbackQuery, Message

from tg_bot.core.database import session_factory

from . import repository
from .schemas import User, UserRole


async def create_from_message(message: CallbackQuery | Message, role: UserRole) -> None:
    """Создаёт пользователя, используя его сообщение

    :param message: Сообщение пользователя
    :param role: Роль, которую выбрал пользователь
    """

    user = User.from_message(message, role)
    async with session_factory() as session:
        repository.add(session, user)
        await session.commit()
