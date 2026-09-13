# pyright: reportOptionalMemberAccess=false, reportReturnType=false

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_service import LLMTextService, Runtime
from src.shared.infra.services import SrvBaseClient

from ...application.dtos import MentorChat
from ...application.repos import ChatRepository
from ..middlewares import (
    ChatCheckpointerMiddleware,
    LemmatizationMiddleware,
    SummarizationMiddleware,
)
from ..prompts import MENTOR_PROMPT, PROMPT_SUMMARIZE_CHAT
from ..schemas import Context
from .state import State

logger = logging.getLogger(__name__)


class MentorAgent:
    def __init__(self, repo: ChatRepository, session: AsyncSession, client: SrvBaseClient):
        self._client = client
        self._repo = repo
        self._session = session

    async def call_agent(self, chat: MentorChat, context: Context) -> str:
        """Выполняет действие `editor`, чтобы поддержать основной сценарий модуля."""
        messages = [
            {"role": "user", "content": f"Теория \n{chat.content_blocks}"},
            {"role": "user", "content": chat.content},
        ]

        agent = LLMTextService(
            client=self._client,
            system_prompt=MENTOR_PROMPT,
            middlewares=[
                LemmatizationMiddleware(),
                SummarizationMiddleware(
                    system_prompt=PROMPT_SUMMARIZE_CHAT,
                    number_of_tokens=70_000,
                ),
                ChatCheckpointerMiddleware(repo=self._repo, session=self._session),
            ],
            runtime=Runtime(context=context, state=State(chat_id=chat.chat_id)),
        )
        result = await agent.invoke(messages=messages)

        return result.raw_text
