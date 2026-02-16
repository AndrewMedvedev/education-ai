from faststream.redis import RedisBroker

from .config import settings


def register_routers(broker: RedisBroker) -> None:
    from tg_bot.features.teacher.course_creation.consumer import router as course_creation_router

    broker.include_router(course_creation_router)


broker = RedisBroker(settings.redis.url)

register_routers(broker)
