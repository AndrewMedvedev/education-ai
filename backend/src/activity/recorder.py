import logging

from src.shared.domain.events import Event

from .domain.models import ActivityLog
from .domain.repos import ActivityLogRepository
from .registry import map_event_to_activity_log

logger = logging.getLogger(__name__)


class ActivityRecorder:
    def __init__(self, activity_repo: ActivityLogRepository) -> None:
        self.activity_repo = activity_repo

    async def record_all(self, events: list[Event]) -> None:
        """
        Записывает и преобразовывает доменные события в запись о бизнес действии.
        """

        activities: list[ActivityLog] = []
        for event in events:
            try:
                activities.append(map_event_to_activity_log(event))
            except KeyError:
                logger.warning(
                    "Mapping for event %s skipped, no such registered activity mappers",
                    type(event).__name__,
                )

        if not activities:
            logger.warning("No such activity mappers")
            return

        await self.activity_repo.create_many(activities)
