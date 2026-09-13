import asyncio

from src.shared.domain.events import Event, EventPublisher


class ConcurrentEventPublisher:
    def __init__(self, publisher: EventPublisher, max_concurrency: int = 10) -> None:
        self._publisher = publisher
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def publish(self, event: Event) -> None:
        async with self._semaphore:
            await self._publisher.publish(event)

    async def publish_all(self, events: list[Event]) -> None:
        async with asyncio.TaskGroup() as tg:
            for event in events:
                tg.create_task(self.publish(event))
