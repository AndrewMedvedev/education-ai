from typing import Any

from collections.abc import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser


class UserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[TgUser]],
            event: TelegramObject,
            data: dict[str, Any]
    ) -> Any:
        tg_user = data.get("event_from_user")
