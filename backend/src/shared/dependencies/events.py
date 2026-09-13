from typing import Annotated

from fastapi import Depends

from src.core.rabbit import broker, rabbit_config
from src.shared.domain.events import EventPublisher
from src.shared.infra.events import RabbitMQEventPublisher


def get_event_publisher() -> EventPublisher:
    return RabbitMQEventPublisher(broker, exchange=rabbit_config.exchange)


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]
