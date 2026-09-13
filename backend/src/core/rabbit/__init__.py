# ruff: file-ignore[non-empty-init-module]
from faststream.rabbit.fastapi import RabbitRouter

from .config import rabbit_config

router = RabbitRouter(url=rabbit_config.uri, virtualhost=rabbit_config.virtualhost)

broker = router.broker

__all__ = ["broker", "rabbit_config", "router"]
