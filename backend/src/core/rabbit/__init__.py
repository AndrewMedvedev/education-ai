from faststream.rabbit import RabbitExchange
from faststream.rabbit.fastapi import RabbitRouter

from .config import rabbit_config

router = RabbitRouter(url=rabbit_config.uri, virtualhost=rabbit_config.virtualhost)

broker = router.broker

events_exchange = RabbitExchange(rabbit_config.exchange, durable=True)

__all__ = ["broker", "events_exchange", "rabbit_config", "router"]
