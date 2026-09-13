from typing import ClassVar, Protocol

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ..utils.time import current_datetime


@dataclass(frozen=True)
class Event:
    """Базовый класс для всех доменных событий."""

    event_type: ClassVar[str]

    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=current_datetime)
    version: int = field(default=1)

    def __post_init__(self):
        if self.version < 1:
            raise ValueError("Event version must be >= 1")


class EventPublisher(Protocol):
    """
    Абстракция для публикации доменных событий.
    Доменный слой знает только об этом интерфейсе.
    """

    async def publish(self, event: Event) -> None:
        """Опубликовать доменное событие."""

    async def publish_all(self, events: list[Event]) -> None:
        """Опубликовать сразу несколько событий (удобно после сохранения агрегата)."""
