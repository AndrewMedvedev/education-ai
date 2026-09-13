from typing import Any

import logging
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket, WebSocketException
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)


class WebsocketManager:
    def __init__(self) -> None:
        self.active_connections: dict[UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        await websocket.accept()
        self.active_connections[user_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: UUID) -> None:
        if websocket in self.active_connections.get(user_id, []):
            self.active_connections[user_id].remove(websocket)

    async def send_to_user(self, user_id: UUID, message: dict[str, Any]) -> None:
        """Отправка уведомления конкретному пользователю"""

        # 1. Проверка активных соединений у пользователя
        if user_id not in self.active_connections:
            return

        # 2. Отправка сообщения пользователю (с обработкой неактивных соединений)
        dead_connections = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(jsonable_encoder(message))
            except WebSocketException:
                logger.warning(
                    "Error occurred while sending message to WS for user with ID %s, "
                    "start kill connection", user_id
                )
                dead_connections.append(connection)

        # 3. Отчистка мёртвых соединений
        for connection in dead_connections:
            self.active_connections[user_id].remove(connection)
