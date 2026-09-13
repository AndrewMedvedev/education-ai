from typing import Any

import asyncio
import logging
from collections import defaultdict
from uuid import UUID

logger = logging.getLogger(__name__)


class SSEManager:
    """
    Управляет активными SSE-соединениями (Server-Sent Events) пользователей.
    Отвечает только за локальную доставку уведомлений (работает только
    в рамках одного процесса).
    """

    def __init__(self) -> None:
        self.local_queues: dict[UUID, set[asyncio.Queue[Any]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, queue: asyncio.Queue[Any]) -> None:
        """Подключение клиента к SSE каналу"""

        async with self._lock:
            self.local_queues[user_id].add(queue)

        logger.info(
            "SSE connected for user %s | Total connections: %s",
            user_id, len(self.local_queues[user_id])
        )

    async def disconnect(self, user_id: UUID, queue: asyncio.Queue[Any]):
        """Отключение клиента"""

        async with self._lock:
            self.local_queues[user_id].discard(queue)
            if not self.local_queues[user_id]:
                self.local_queues.pop(user_id, None)

        logger.info("SSE disconnected for user %s", user_id)

    async def send_to_user(self, user_id: UUID, message: Any) -> None:
        """Отправка сообщения подключенному пользователю"""

        # 1. Проверка есть ли у пользователя локальное соединение
        if user_id not in self.local_queues:
            return

        # 2. Объявление 'мёртвых' соединений
        dead_queues: list[asyncio.Queue[Any]] = []

        # 3. Отправка во все соединения
        for queue in list(self.local_queues[user_id]):
            try:
                await queue.put(message)
            except asyncio.QueueShutDown:
                dead_queues.append(queue)

        # 4. Удаление 'мёртвых' соединений
        if dead_queues:
            async with self._lock:
                for queue in dead_queues:
                    self.local_queues[user_id].discard(queue)
