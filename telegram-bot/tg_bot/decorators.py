from typing import Any, Literal

from collections.abc import Awaitable, Callable
from functools import wraps

from aiogram import Bot


def telegram_bot_notifier(
        bot: Bot,
        recipient_id: int,
        message_text: str,
        mode: Literal["before", "after"] = "after"
):
    """Декоратор для отправки сообщения в Telegram.

    :param bot: Экземпляр aiogram бота.
    :param recipient_id: Telegram UserId получателя.
    :param message_text: Текст сообщения.
    :param mode: `before` - отправка до вызова функции, `after` - после.
    """

    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if mode == "before":
                await bot.send_message(chat_id=recipient_id, text=message_text)
            result = await func(*args, **kwargs)
            if mode == "after":
                await bot.send_message(chat_id=recipient_id, text=message_text)
            return result
        return wrapper
    return decorator
