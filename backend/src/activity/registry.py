from typing import TypeVar

from collections.abc import Callable

from src.shared.domain.events import Event

from .domain.models import ActivityLog

EventType = TypeVar("EventType", bound=Event)

ActivityLogMapper = Callable[[EventType], ActivityLog]

_activity_mappers_registry: dict[type[EventType], ActivityLogMapper] = {}


def register_activity_log_mapper[T: Event](
        event_type: type[T],
) -> Callable[[ActivityLogMapper[T]], ActivityLogMapper[T]]:

    def decorator(func: ActivityLogMapper[T]) -> ActivityLogMapper[T]:
        _activity_mappers_registry[event_type] = func
        return func

    return decorator


def map_event_to_activity_log[T: Event](event: T) -> ActivityLog:
    return _activity_mappers_registry[type(event)](event)
