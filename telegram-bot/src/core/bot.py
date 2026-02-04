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
    from src.features.commons.handlers import router as common_router  # noqa: PLC0415
    from src.features.teacher.course_creation.handlers import (  # noqa: PLC0415
        router as course_creation_router,
    )
    from src.features.teacher.handlers import router as teacher_router  # noqa: PLC0415

    dispatcher.include_routers(common_router, teacher_router, course_creation_router)
