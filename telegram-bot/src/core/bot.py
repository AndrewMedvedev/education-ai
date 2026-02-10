from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import settings

bot = Bot(
    token=settings.telegram.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()

dp = Dispatcher(storage=storage)


def register_handlers(dispatcher: Dispatcher) -> None:
    from src.features.commons.handlers import router as common_router
    from src.features.teacher.course_creation.handlers import (
        router as course_creation_router,
    )
    from src.features.teacher.handlers import router as teacher_router
    from src.features.teacher.students_management.handlers import (
        router as students_management_router,
    )

    dispatcher.include_routers(
        common_router,
        teacher_router,
        course_creation_router,
        students_management_router,
    )


register_handlers(dp)
