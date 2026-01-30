from faststream import FastStream
from faststream.redis import RedisBroker

from .config import settings

broker = RedisBroker(settings.redis.url)


def get_faststream_app() -> FastStream:
    from src.features.teacher.course_creation.tasks import (  # noqa: PLC0415
        router as course_creation_router,
    )

    broker.include_router(course_creation_router)
    return FastStream(broker)


faststream_app = get_faststream_app()
