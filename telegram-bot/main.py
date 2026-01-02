import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.settings import settings

WEBHOOK_URL = f"{settings.ngrok.url}/hook"

logger = logging.getLogger(__name__)

bot = Bot(token=settings.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher(storage=MemoryStorage())


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await bot.set_webhook(
        url=WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=True
    )
    logger.info("Webhook set to %s", WEBHOOK_URL)
    yield
    await bot.delete_webhook()
    logger.info("Webhook removed")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/hook")
async def handle_telegram_bot_update(request: Request) -> None:
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)


if __name__ == "__main__":
    configure_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
