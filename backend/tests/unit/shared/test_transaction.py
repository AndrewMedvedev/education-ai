from unittest.mock import AsyncMock

import pytest

from src.shared.application.transaction import Transaction
from src.shared.domain.entities import Entity
from src.shared.domain.events import Event


@pytest.mark.asyncio
async def test_transaction_records_commits_and_publishes_entity_events():
    """Сохраняет activity, коммитит и только потом публикует события."""
    entity = Entity()
    event = Event()
    entity.register_event(event)
    recorder = AsyncMock()
    unit_of_work = AsyncMock()
    publisher = AsyncMock()
    calls = []

    async def record_all(events):
        calls.append(("record", events))

    async def commit():
        calls.append(("commit", None))

    async def publish_all(events):
        calls.append(("publish", events))

    recorder.record_all.side_effect = record_all
    unit_of_work.commit.side_effect = commit
    publisher.publish_all.side_effect = publish_all
    transaction = Transaction(unit_of_work, publisher, recorder)

    await transaction(entity)

    assert calls == [("record", [event]), ("commit", None), ("publish", [event])]
