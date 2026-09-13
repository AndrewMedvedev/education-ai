import logging

from pydantic import BaseModel, Field

from src.llm_service import LLMTextService, Runtime, tool
from src.shared.infra.services import SrvBaseClient

from ...middlewares import LemmatizationMiddleware, ToolCallLimitMiddleware
from ...schemas import Context
from ..tools import browse_page, knowledge_search, save_knowledge, web_search
from .prompts import CRITIC_PROMPT, REASONER_PROMPT, RESEARCHER_PROMPT

logger = logging.getLogger(__name__)


@tool(name="call_critique_agent", description="Вызвать агента критика")
async def call_critique_agent(runtime: Runtime[Context, SrvBaseClient]) -> dict:
    logger.info("Call critique agent")
    prompt = runtime.context.prompt
    critic_agent = LLMTextService(
        client=runtime.state,  # pyright: ignore[reportArgumentType]
        system_prompt=CRITIC_PROMPT.format(prompt=prompt),
    )
    result = await critic_agent.invoke(messages=runtime.messages)
    return {"role": "assistant", "content": result.raw_text}


class ResearchInput(BaseModel):
    task: str = Field(description="Задача для исследования")


@tool(name="call_researcher_agent", description="Вызвать агента исследователя")
async def call_researcher_agent(
    runtime: Runtime[Context, SrvBaseClient],
    schema: ResearchInput,
) -> dict:
    logger.info("Call researcher agent")
    researcher_agent = LLMTextService(
        client=runtime.state,  # pyright: ignore[reportArgumentType]
        system_prompt=RESEARCHER_PROMPT,
        tools={
            "knowledge_search": knowledge_search,
            "web_search": web_search,
            "browse_page": browse_page,
            "save_knowledge": save_knowledge,
        },
        runtime=Runtime(context=runtime.context, state=runtime.state),
        middlewares=[
            ToolCallLimitMiddleware(
                tool_limits={"web_search": 4, "browse_page": 5, "knowledge_search": 5}
            ),
            LemmatizationMiddleware(),
        ],
    )
    result = await researcher_agent.invoke(messages=[{"role": "user", "content": schema.task}])
    return {"role": "assistant", "content": result.raw_text}


def reasoner_agent(runtime: Runtime[Context, SrvBaseClient]) -> LLMTextService:

    return LLMTextService(
        client=runtime.state,  # pyright: ignore[reportArgumentType]
        system_prompt=REASONER_PROMPT.format(prompt=runtime.context.prompt),
        tools={
            "call_researcher_agent": call_researcher_agent,
            "call_critique_agent": call_critique_agent,
        },
        middlewares=[
            LemmatizationMiddleware(),
            ToolCallLimitMiddleware(tool_limits={"call_researcher_agent": 2}),
        ],
        runtime=runtime,
    )
