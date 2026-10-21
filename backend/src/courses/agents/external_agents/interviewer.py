# pyright: reportOptionalMemberAccess=false, reportReturnType=false

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_service import LLMTextService, Runtime, StructuredTool

from ...application.repos import ChatRepository
from ...infra.services.client import SrvCourseClient
from ..middlewares import (
    ChatCheckpointerMiddleware,
    StopInterview,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from ..prompts import PROMPT_SUMMARIZE_CHAT
from ..schemas import Context
from ..tools import (
    State,
    get_content,
    get_table_of_contents,
    get_titles,
)

logger = logging.getLogger(__name__)


class InterviewerAgent:
    def __init__(
        self,
        client: SrvCourseClient,
        session: AsyncSession,
        repo: ChatRepository,
        system_prompt: str,
        tools: dict[str, StructuredTool],
        tool_limits: dict[str, int],
    ):
        self._client = client
        self._session = session
        self._repo = repo
        self._system_prompt = system_prompt
        self._tools = tools
        self._tool_limits = tool_limits

    async def call_agent(self, chat_id: UUID, context: Context) -> str:
        agent = LLMTextService(
            client=self._client,
            system_prompt=self._system_prompt,
            tools={
                **self._tools,
                "get_table_of_contents": get_table_of_contents,
                "get_titles": get_titles,
                "get_content": get_content,
            },
            middlewares=[
                ChatCheckpointerMiddleware(repo=self._repo, session=self._session),
                SummarizationMiddleware(
                    system_prompt=PROMPT_SUMMARIZE_CHAT,
                    number_of_tokens=70_000,
                ),
                ToolCallLimitMiddleware(
                    tool_limits={
                        **self._tool_limits,
                        "get_table_of_contents": 3,
                        "get_titles": 6,
                        "get_content": 12,
                    }
                ),
                StopInterview(),
            ],
            runtime=Runtime(
                context=context,
                state=State(
                    chat_id=chat_id,
                    db_session=self._session,
                    client=self._client,
                ),
            ),
        )
        result = await agent.invoke(messages=[{"role": "user", "content": context.prompt}])
        return result.raw_text
