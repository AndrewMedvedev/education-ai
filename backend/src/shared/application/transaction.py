from src.activity.recorder import ActivityRecorder
from src.shared.domain.entities import Entity
from src.shared.domain.events import EventPublisher

from .uow import UnitOfWork


class Transaction:
    def __init__(
        self,
        uow: UnitOfWork,
        publisher: EventPublisher,
        recorder: ActivityRecorder | None = None,
    ) -> None:
        self._uow = uow
        self._publisher = publisher
        self._recorder = recorder

    async def __call__(self, *entities: Entity) -> None:
        events = []
        for entity in entities:
            events.extend(entity.collect_events())

        if self._recorder is not None:
            await self._recorder.record_all(events)

        await self._uow.commit()

        await self._publisher.publish_all(events)
