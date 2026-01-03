from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from ..settings import settings
from .handlers import router

bot = Bot(token=settings.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher(storage=MemoryStorage())

dp.include_router(router)
