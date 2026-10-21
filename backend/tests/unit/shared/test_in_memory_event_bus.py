import asyncio

import pytest

from src.shared.domain.events import Event
from src.shared.infra.events.in_memory import ImMemoryEventBus


@pytest.mark.asyncio
async def test_event_bus_delivers_published_event_to_subscriber():
    """Передаёт опубликованное событие подписанному обработчику."""
    bus = ImMemoryEventBus()
    delivered = asyncio.Event()
    event = Event()

    async def handler(received_event: Event) -> None:
        assert received_event is event
        delivered.set()

    bus.subscribe(Event, handler)
    await bus.start()
    try:
        await bus.publish(event)

        await asyncio.wait_for(delivered.wait(), timeout=1)
    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_event_bus_continues_dispatching_after_handler_error():
    """Не прерывает доставку события другим обработчикам при ошибке одного из них."""
    bus = ImMemoryEventBus()
    delivered = asyncio.Event()
    event = Event()

    def failed_handler(_: Event) -> None:
        raise RuntimeError("Handler failed")

    async def successful_handler(_: Event) -> None:
        delivered.set()

    bus.subscribe(Event, failed_handler)
    bus.subscribe(Event, successful_handler)
    await bus.start()
    try:
        await bus.publish(event)

        await asyncio.wait_for(delivered.wait(), timeout=1)
    finally:
        await bus.stop()
