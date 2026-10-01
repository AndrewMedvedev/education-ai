from typing import Annotated

from fastapi import Depends

from src.core.rabbit import broker, events_exchange
from src.shared.domain.events import EventPublisher
from src.shared.infra.events import RabbitMQEventPublisher


def get_event_publisher() -> EventPublisher:
    return RabbitMQEventPublisher(
        broker,
        exchange=events_exchange,
    )


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]
