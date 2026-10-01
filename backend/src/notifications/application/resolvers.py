import logging
from uuid import UUID

from ..domain.vo import ChannelType, NotificationType
from .channels import NotificationChannel
from .repos import PreferenceRepository

logger = logging.getLogger(__name__)


class ChannelResolver:
    def __init__(
        self,
        preference_repo: PreferenceRepository,
        *channels: NotificationChannel,
    ) -> None:
        self.preference_repo = preference_repo
        self.channels: dict[ChannelType, NotificationChannel] = {
            channel.channel_type: channel for channel in channels
        }

    async def resolve(
        self,
        user_id: UUID,
        notification_type: NotificationType,
    ) -> list[NotificationChannel]:
        """Возвращает список каналов, на которые нужно отправить уведомление"""

        # 1. Получение настроек пользователя (на заданное уведомление)
        preference = await self.preference_repo.get_for_notification(user_id, notification_type)

        # 2. Если настроек нет - все каналы доступны
        if preference is None:
            return list(self.channels.values())

        # 3. Фильтрация разрешённых каналов
        allowed_channels = []
        for channel_type, channel in self.channels.items():
            if preference.is_enabled_for_channel(channel_type):
                allowed_channels.append(channel)

        return allowed_channels
