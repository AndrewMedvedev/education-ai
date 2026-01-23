import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from ..bot import bot, dp
from ..settings import PROJECT_ROOT, settings
from .api.routers import router as api_router
from .routers import router

WEBAPP_DIR = PROJECT_ROOT / "src" / "webapp"
TEMPLATES_DIR = WEBAPP_DIR / "templates"
STATIC_DIR = WEBAPP_DIR / "static"
WEBHOOK_URL = f"{settings.ngrok.url}/hook"

logger = logging.getLogger(__name__)


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

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.include_router(router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/hook")
async def handle_aiogram_bot_update(request: Request) -> None:
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)
