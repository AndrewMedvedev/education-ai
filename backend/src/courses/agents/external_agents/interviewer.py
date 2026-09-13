# pyright: reportOptionalMemberAccess=false, reportReturnType=false

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_service import LLMTextService, Runtime
from src.shared.infra.services import SrvBaseClient

from ...application.repos import ChatRepository
from ..middlewares import (
    ChatCheckpointerMiddleware,
    LemmatizationMiddleware,
    StopInterview,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from ..prompts import INTERVIEWER_PROMPT, PROMPT_SUMMARIZE_CHAT
from ..schemas import Context
from ..tools import (
    State,
    complete_interview,
    get_content,
    get_table_of_contents,
    get_titles,
)

logger = logging.getLogger(__name__)


class InterviewerAgent:
    def __init__(self, repo: ChatRepository, session: AsyncSession, client: SrvBaseClient):
        self._client = client
        self._repo = repo
        self._session = session

    async def call_agent(self, chat_id: UUID, context: Context) -> str:
        """Выполняет действие `interviewer`, чтобы поддержать основной сценарий модуля."""
        agent = LLMTextService(
            client=self._client,
            system_prompt=INTERVIEWER_PROMPT,
            tools={
                "complete_interview": complete_interview,
                "get_table_of_contents": get_table_of_contents,
                "get_titles": get_titles,
                "get_content": get_content,
            },
            middlewares=[
                LemmatizationMiddleware(),
                SummarizationMiddleware(
                    system_prompt=PROMPT_SUMMARIZE_CHAT,
                    number_of_tokens=70_000,
                ),
                ToolCallLimitMiddleware(
                    tool_limits={
                        "complete_interview": 1,
                        "get_table_of_contents": 3,
                        "get_titles": 6,
                        "get_content": 12,
                    }
                ),
                ChatCheckpointerMiddleware(repo=self._repo, session=self._session),
                StopInterview(),
            ],
            runtime=Runtime(
                context=context, state=State(chat_id=chat_id, db_session=self._session)
            ),
        )
        result = await agent.invoke(messages=[{"role": "user", "content": context.prompt}])
        return result.raw_text
