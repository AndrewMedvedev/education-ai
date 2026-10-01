# pyright: reportReturnType=false
from typing import Annotated

from fastapi import Depends

from src.core.rabbit import broker
from src.shared.dependencies.database import DBSession
from src.shared.dependencies.mail import mail_client

from ..application.channels import EmailChannel, InAppChannel, NotificationChannel
from ..infra.database.repos.notification import SqlNotificationRepository
from ..infra.database.repos.user_preference import SqlUserPreferenceRepository


def get_email_channel() -> NotificationChannel:
    return EmailChannel(mail_sender=mail_client)


def get_in_app_channel() -> NotificationChannel:
    return InAppChannel(broker)


def get_notification_repo(session: DBSession) -> SqlNotificationRepository:
    return SqlNotificationRepository(session)


def get_preference_repo(session: DBSession) -> SqlUserPreferenceRepository:
    return SqlUserPreferenceRepository(session)


EmailChannelDep = Annotated[NotificationChannel, Depends(get_email_channel)]
InAppChannelDep = Annotated[NotificationChannel, Depends(get_in_app_channel)]
NotificationRepoDep = Annotated[SqlNotificationRepository, Depends(get_notification_repo)]
PreferenceRepoDep = Annotated[SqlUserPreferenceRepository, Depends(get_preference_repo)]
