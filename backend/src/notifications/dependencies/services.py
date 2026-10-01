# pyright: reportArgumentType=false
from typing import Annotated

from fastapi import Depends

from src.shared.dependencies.database import DBSession

from ..application.resolvers import ChannelResolver
from ..application.services import NotificationService
from .base import EmailChannelDep, InAppChannelDep, NotificationRepoDep, PreferenceRepoDep


def get_channel_resolver(
    preference_repo: PreferenceRepoDep,
    email_channel: EmailChannelDep,
    in_app_channel: InAppChannelDep,
) -> ChannelResolver:
    return ChannelResolver(preference_repo, email_channel, in_app_channel)


ChannelResolverDep = Annotated[ChannelResolver, Depends(get_channel_resolver)]


def get_notification_service(
    session: DBSession,
    repository: NotificationRepoDep,
    channel_resolver: ChannelResolverDep,
    email_channel: EmailChannelDep,
) -> NotificationService:
    return NotificationService(
        session=session,
        repository=repository,
        channel_resolver=channel_resolver,
        email_channel=email_channel,
    )


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
