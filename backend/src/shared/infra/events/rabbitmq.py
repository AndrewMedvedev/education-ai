import logging

from faststream.rabbit import RabbitBroker

from src.shared.domain.events import Event

logger = logging.getLogger(__name__)


class RabbitMQEventPublisher:
    def __init__(self, broker: RabbitBroker, exchange: str) -> None:
        self._broker = broker
        self._exchange = exchange

    async def publish(self, event: Event) -> None:
        await self._broker.publish(event, exchange=self._exchange, routing_key=event.event_type)

    async def publish_all(self, events: list[Event]) -> None:
        for event in events:
            await self.publish(event)
