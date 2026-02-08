import logging
from contextlib import asynccontextmanager

import markdown.extensions.fenced_code
import markdown.extensions.tables
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown import markdown as md

from .bot import bot, dp
from .broker import broker
from .config import BASE_DIR, settings

STATIC_DIR = BASE_DIR / "static"  # Статический контент (CSS, JS, ...)
TEMPLATES_DIR = BASE_DIR / "templates"  # Jinja шаблоны
WEBHOOK_ENDPOINT = f"{settings.app.url}{settings.telegram.webhook_path}"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bot.set_webhook(WEBHOOK_ENDPOINT)
    logger.info("Telegram bot webhook set to %s", WEBHOOK_ENDPOINT)
    await broker.start()
    yield
    await bot.delete_webhook()
    logger.info("Telegram bot webhook deleted")
    await broker.stop()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

templates.env.filters["markdown"] = lambda text: md(
    text,
    extensions=[
        "fenced_code",
        "tables",
        "nl2br",
        "sane_lists",
        "mdx_math",
        "codehilite",
        "attr_list"
    ],
    extension_configs={
        "codehilite": {
            "use_pygments": False,
            "css_class": "hljs"
        }
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post(settings.telegram.webhook_path)
async def bot_webhook(request: Request) -> None:
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)
