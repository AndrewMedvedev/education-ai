import logging

from faststream.rabbit import RabbitQueue

from src.core.rabbit import events_exchange, router
from src.courses.domain.events import CourseInvited
from src.iam.domain.events import UserInvited
from src.notifications.application.factories import (
    from_course_invited,
    from_organization_invited,
    from_user_invited,
)
from src.notifications.dependencies.services import NotificationServiceDep
from src.notifications.domain.entities import Notification
from src.organization.domain.events import OrganizationInvited
from src.shared.dependencies import sse_manager

logger = logging.getLogger(__name__)


@router.subscriber(
    queue=RabbitQueue("notifications.sse", durable=True, exclusive=False),
    description="Отправка уведомления в локальную очередь",
)
async def handle_notification(notification: Notification) -> None:
    await sse_manager.send_to_user(notification.user_id, notification)  # pyright: ignore[reportArgumentType]


@router.subscriber(
    queue=RabbitQueue("courses.invited", durable=True),
    exchange=events_exchange,
)
async def on_course_invited(
    event: CourseInvited,
    service: NotificationServiceDep,
) -> None:
    notification = from_course_invited(event)
    await service.notify(notification)


@router.subscriber(
    queue=RabbitQueue("organizations.invited", durable=True),
    exchange=events_exchange,
)
async def on_organization_invited(
    event: OrganizationInvited,
    service: NotificationServiceDep,
) -> None:
    notification = from_organization_invited(event)
    await service.notify(notification)


@router.subscriber(
    queue=RabbitQueue("users.invited", durable=True),
    exchange=events_exchange,
)
async def on_user_invited(
    event: UserInvited,
    service: NotificationServiceDep,
) -> None:
    notification = from_user_invited(event)
    await service.notify(notification)
