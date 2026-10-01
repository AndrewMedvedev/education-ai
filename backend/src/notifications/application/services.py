import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import NotFoundError

from ..domain.entities import Notification
from ..domain.exceptions import NotificationSendingFailedError
from .channels import EmailChannel
from .repos import NotificationRepository
from .resolvers import ChannelResolver

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        repository: NotificationRepository,
        channel_resolver: ChannelResolver,
        email_channel: EmailChannel,
    ) -> None:
        self.session = session
        self.repository = repository
        self.channel_resolver = channel_resolver
        self.email_channel = email_channel

    async def notify(self, notification: Notification) -> None:
        """Отправка уведомления через все подходящие каналы"""

        # 1. Сохранение сущности
        await self.repository.create(notification)
        await self.session.commit()
        if notification.user_id is None:
            try:
                await self.email_channel.send(notification)
                return  # noqa: TRY300
            except NotificationSendingFailedError:
                logger.exception("Notification sending failed")
                return

        # 2. Отправка уведомления во все подходящие каналы
        channels = await self.channel_resolver.resolve(
            user_id=notification.user_id,
            notification_type=notification.type,
        )
        for channel in channels:
            try:
                await channel.send(notification)
            except NotificationSendingFailedError:
                logger.exception("Notification sending failed")

    async def mark_as_read(self, notification_id: UUID, read_by: UUID) -> Notification:
        notification = await self.repository.read(notification_id)
        if notification is None:
            raise NotFoundError(f"Notification with ID {notification_id} not found")

        if not notification.read:
            notification.mark_as_read(read_by)
            await self.repository.update(notification)
            await self.session.commit()
        else:
            logger.warning("Notification with ID %s already marked as read", notification_id)

        return notification
