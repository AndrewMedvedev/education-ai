from typing import ClassVar, Protocol

import logging

from faststream.rabbit import RabbitBroker

from src.shared.domain.exceptions import EmailSendingFailedError
from src.shared.infra.mail import SmtpMailClient

from ..domain.entities import Notification
from ..domain.exceptions import NotificationSendingFailedError
from ..domain.vo import ChannelType, NotificationType

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    channel_type: ClassVar[ChannelType]

    async def send(self, notification: Notification) -> None:
        """Отправить уведомление через текущий канал"""


# Маппинг типов уведомлений к email шаблону
EMAIL_TEMPLATE_MAP: dict[NotificationType, str] = {
    NotificationType.COURSE_INVITED: "email/course_invite.html",
    NotificationType.ORGANIZATION_INVITED: "email/organization_invite.html",
    NotificationType.INVITED_IN_SYSTEM: "email/invite_in_system.html",
}


class EmailChannel:
    channel_type = ChannelType.EMAIL

    def __init__(self, mail_sender: SmtpMailClient) -> None:
        self.mail_sender = mail_sender

    async def send(self, notification: Notification) -> None:
        template_name = EMAIL_TEMPLATE_MAP.get(notification.type)
        if template_name is None:
            logger.warning(
                "No such template registered for this notification type_ - '%s'",
                notification.type.value,
            )
        try:
            await self.mail_sender.send(
                to=notification.email.value,
                subject=notification.title,
                plain_text=notification.message,
                template_name=template_name,
                context=None if template_name is None else notification.data,
            )
        except EmailSendingFailedError as e:
            raise NotificationSendingFailedError(
                "Error occurred while sending to email channel"
            ) from e


class InAppChannel:
    channel_type = ChannelType.IN_APP

    def __init__(self, broker: RabbitBroker) -> None:
        self.broker = broker

    async def send(self, notification: Notification) -> None:
        await self.broker.publish(notification, queue="notifications.sse")
