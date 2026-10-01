from typing import Annotated

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.encoders import jsonable_encoder
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination
from src.shared.dependencies import sse_manager
from src.shared.dependencies.params import PaginationDep

from ...application.dtos import UnreadCountOut
from ...dependencies.base import NotificationRepoDep
from ...dependencies.services import NotificationServiceDep
from ...domain.entities import Notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Уведомления"])


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    summary="Получение моих уведомлений",
)
async def get_my_notifications(
    identity: CurrentIdentity,
    repository: NotificationRepoDep,
    pagination: PaginationDep,
    unread_only: Annotated[bool, Query(..., description="Учитывать только непрочитанные")] = False,
) -> Page[Notification]:
    return await repository.get_by_user(identity.id, pagination, unread_only)


@router.get(
    path="/unread-count",
    status_code=status.HTTP_200_OK,
    summary="Получение количества непрочитанных уведомлений",
)
async def get_unread_count(
    identity: CurrentIdentity,
    repository: NotificationRepoDep,
) -> UnreadCountOut:
    return UnreadCountOut(unread_count=await repository.get_unread_count(identity.id))


@router.patch(
    path="/{notification_id}/read",
    status_code=status.HTTP_200_OK,
    summary="Пометить уведомление как прочитанное",
)
async def mark_as_read(
    notification_id: UUID,
    identity: CurrentIdentity,
    service: NotificationServiceDep,
) -> Notification:
    return await service.mark_as_read(notification_id, read_by=identity.id)


@router.get(
    path="/stream",
    response_class=EventSourceResponse,
    summary="Соединение для отправки уведомлений",
)
async def notification_stream(
    request: Request,
    identity: CurrentIdentity,
    repository: NotificationRepoDep,
):
    # Инициализация подключения
    queue: asyncio.Queue[Notification] = asyncio.Queue(maxsize=10)
    await sse_manager.connect(identity.id, queue)

    async def event_generator():

        try:
            # 1. Отправка последних непрочитанных уведомлений при подключении
            unread_notifications = await repository.get_by_user(
                user_id=identity.id,
                pagination=Pagination(page=1, size=50),
                unread_only=True,
            )
            for notification in unread_notifications.items:
                payload = {
                    "type_": "notification",
                    "notification": jsonable_encoder(notification),
                }
                yield ServerSentEvent(data=payload)

            # 2. Основной цикл прослушивания очереди
            while True:
                if await request.is_disconnected():
                    logger.debug("Client disconnected (SSE)")
                    break

                try:
                    # Ожидание сообщения из очереди
                    message = await asyncio.wait_for(queue.get(), timeout=25.0)
                    payload = {
                        "type_": "notification",
                        "notification": jsonable_encoder(message),
                    }
                    yield ServerSentEvent(data=payload)
                except TimeoutError:
                    # Heartbeat - для удержания соединения
                    yield ServerSentEvent(comment="ping")

        finally:
            # Всегда отключаем пользователя при завершении
            await sse_manager.disconnect(identity.id, queue)

    return EventSourceResponse(event_generator(), ping=20)
