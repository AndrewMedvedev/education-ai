from .domain.models import ActivityLog
from .schemas import ActivityLogResponse


def map_activity_log_to_response(activity_log: ActivityLog) -> ActivityLogResponse:
    return ActivityLogResponse(
        aggregate_type=activity_log.aggregate_type,
        aggregate_id=activity_log.aggregate_id,
        action=activity_log.action,
        actor_id=activity_log.actor_id,
        occurred_at=activity_log.occurred_on,
        changes=activity_log.changes,
        meta=activity_log.meta,
        event_id=activity_log.event_id,
        correlation_id=activity_log.correlation_id,
    )
