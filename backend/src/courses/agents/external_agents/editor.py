# pyright: reportOptionalMemberAccess=false, reportReturnType=false

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_service import Runtime
from src.shared.infra.services import SrvBaseClient

from ...application.dtos import EditorChat
from ...application.repos import ChatRepository
from ...domain.entities import AnyContentBlock
from ...domain.vo import ContentType
from ..course_generator.subagents.theorist import generate_image, generate_text
from ..middlewares import (
    ChatCheckpointerMiddleware,
    SummarizationMiddleware,
)
from ..prompts import PROMPT_SUMMARIZE_CHAT
from ..schemas import Context
from .state import State

logger = logging.getLogger(__name__)


class EditorAgent:
    def __init__(self, repo: ChatRepository, session: AsyncSession, client: SrvBaseClient):
        self._client = client
        self._repo = repo
        self._session = session

    async def call_agent(self, chat: EditorChat, context: Context) -> AnyContentBlock:
        """Выполняет действие `editor`, чтобы поддержать основной сценарий модуля."""
        messages = json.dumps(
            [
                {"role": "user", "content": f"Теория \n{chat.content_blocks}"},
                {
                    "role": "user",
                    "content": f"Контент который нужно изменить\n{chat.content_block}",
                },
                {"role": "user", "content": chat.content},
            ],
            ensure_ascii=False,
        )

        runtime = Runtime(context=context, state=State(chat_id=chat.chat_id))

        # if chat.content_type == ContentType.IMAGE:
        #     return await generate_image(
        #         client=self._client,
        #         content_type=chat.content_type,
        #         context=context,
        #         images=chat.images,
        #         prompt=chat.content,
        #         runtime=runtime,
        #         middlewares=[
        #             SummarizationMiddleware(
        #                 system_prompt=PROMPT_SUMMARIZE_CHAT,
        #                 number_of_tokens=30_000,
        #             ),
        #             ChatCheckpointerMiddleware(repo=self._repo, session=self._session),
        #         ],
        #     )

        return await generate_text(
            client=self._client,
            content_type=chat.content_type,
            context=context,
            prompt=messages,
            middlewares=[
                SummarizationMiddleware(
                    system_prompt=PROMPT_SUMMARIZE_CHAT,
                    number_of_tokens=80_000,
                ),
                ChatCheckpointerMiddleware(repo=self._repo, session=self._session),
            ],
            runtime=runtime,
        )
