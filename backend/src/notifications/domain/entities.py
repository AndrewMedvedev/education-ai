from typing import Any

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from src.shared.domain.vo import Email

from ...iam.domain.exceptions import PermissionDeniedError
from ...shared.domain.entities import Entity
from ...shared.utils.time import current_datetime
from .vo import ChannelType, NotificationType


@dataclass(kw_only=True)
class Notification(Entity):
    """
    Уведомление пользователю о событие в системе
    """

    email: Email
    user_id: UUID | None = None
    title: str
    message: str
    type: NotificationType
    read: bool = field(default=False)
    data: dict[str, Any] = field(default_factory=dict)  # Дополнительные данные

    def mark_as_read(self, read_by: UUID) -> None:
        """Пометить как прочитанное"""

        if read_by != self.user_id:
            raise PermissionDeniedError("You can only read your notifications")

        if not self.read:
            self.read = True
            self.updated_at = current_datetime()


@dataclass(kw_only=True)
class UserPreference(Entity):
    """
    Настройки уведомлений для конкретного пользователя
    """

    user_id: UUID
    notification_type: NotificationType

    # По каким каналам получать уведомления
    enabled_channels: set[ChannelType] = field(default_factory=set)

    # Дополнительные настройки
    muted_until: datetime | None = None

    def __post_init__(self) -> None:
        # 1. Добавление каналов по умолчанию
        if not self.enabled_channels:
            self.enabled_channels = {ChannelType.EMAIL, ChannelType.IN_APP}

    @property
    def is_muted(self) -> bool:
        """Активно ли временное отключение прямо сейчас"""

        return self.muted_until is not None and self.muted_until > current_datetime()

    def is_enabled_for_channel(self, channel: ChannelType) -> bool:
        """
        Проверяет, включён ли канал для данного типа уведомления
        """

        # 1. Если уведомления отключены, то канал недоступен
        if self.is_muted:
            return False

        # 2. Проверка каналов
        return channel in self.enabled_channels

    def disable_channel(self, channel: ChannelType) -> None:
        """Отключение уведомлений для конкретного канала"""

        if channel not in self.enabled_channels:
            return

        self.enabled_channels.discard(channel)
        self.updated_at = current_datetime()

    def enable_channel(self, channel: ChannelType) -> None:
        """Подключение уведомлений через конкретный канал"""

        if channel in self.enabled_channels:
            return

        self.enabled_channels.add(channel)
        self.updated_at = current_datetime()

    def mute(self, duration: timedelta) -> None:
        """
        Отключение уведомлений от всех каналов на определённый промежуток времени
        """

        if current_datetime() + duration <= current_datetime():
            raise ValueError("Mute until must be in the future")

        self.muted_until = current_datetime() + duration
        self.updated_at = current_datetime()

    def unmute(self) -> None:
        """Снимает временное отключение уведомлений"""

        if self.muted_until is not None:
            self.muted_until = None
            self.updated_at = current_datetime()
