from dataclasses import dataclass, field
from typing import ClassVar
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.activity.domain.models import ActivityLog
from src.activity.recorder import ActivityRecorder
from src.activity.registry import register_activity_log_mapper
from src.shared.domain.events import Event


@dataclass(frozen=True)
class ActivityTestEvent(Event):
    event_type: ClassVar[str] = "activity.test"

    actor_id: UUID = field(default_factory=uuid4)
    aggregate_id: UUID = field(default_factory=uuid4)


@pytest.mark.asyncio
async def test_record_all_saves_activity_for_registered_event():
    """Преобразует зарегистрированное событие в запись activity."""
    repository = AsyncMock()
    event = ActivityTestEvent()

    @register_activity_log_mapper(ActivityTestEvent)
    def map_activity_event(value: ActivityTestEvent) -> ActivityLog:
        return ActivityLog(
            aggregate_type="course",
            aggregate_id=value.aggregate_id,
            action="created",
            actor_id=value.actor_id,
            event_id=value.event_id,
        )

    recorder = ActivityRecorder(repository)

    await recorder.record_all([event])

    activity = repository.create_many.await_args.args[0][0]
    assert activity.aggregate_type == "course"
    assert activity.aggregate_id == event.aggregate_id
    assert activity.actor_id == event.actor_id
    assert activity.event_id == event.event_id


@pytest.mark.asyncio
async def test_record_all_skips_events_without_registered_mapper():
    """Не создаёт activity для события без зарегистрированного маппера."""
    repository = AsyncMock()
    recorder = ActivityRecorder(repository)

    await recorder.record_all([Event()])

    repository.create_many.assert_not_awaited()
