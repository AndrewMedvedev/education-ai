from faststream.redis import RedisBroker

from .config import settings


def register_routers(broker: RedisBroker) -> None:
    from src.features.teacher.course_creation.broker import router as course_creation_router

    broker.include_router(course_creation_router)


broker = RedisBroker(settings.redis.url)

register_routers(broker)
