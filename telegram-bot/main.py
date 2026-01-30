import asyncio
import logging

from src.core.bot import bot, dp, register_handlers
from src.core.broker import faststream_app


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s",
    )


async def start_aiogram_bot() -> None:
    register_handlers(dp)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def main() -> None:
    await asyncio.gather(faststream_app.broker.start(), start_aiogram_bot())


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
