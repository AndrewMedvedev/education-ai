import logging
from datetime import datetime

from pydantic import BaseModel, Field

from src.courses.agents.middlewares import (
    ToolCallLimitMiddleware,
    ToolOutputCompressionMiddleware,
)
from src.courses.agents.schemas import Context
from src.courses.infra.services.client import SrvCourseClient
from src.llm_service import LLMTextService, Runtime, tool

from ..tools import browse_page, knowledge_search, save_knowledge, web_search
from .prompts import CRITIC_PROMPT, REASONER_PROMPT, RESEARCHER_PROMPT

logger = logging.getLogger(__name__)


@tool(name="call_critique_agent", description="Вызвать агента критика")
async def call_critique_agent(runtime: Runtime[Context, SrvCourseClient]) -> dict:
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


class ResearchFact(BaseModel):
    claim: str = Field(
        description="Краткое утверждение, которое можно включить в учебный материал"
    )
    evidence: str = Field(
        description="Выдержка или конкретное содержание источника, подтверждающее утверждение"
    )
    source_title: str = Field(description="Название документа или страницы")
    source_organization: str | None = Field(
        default=None,
        description="Организация — автор или издатель источника",
    )
    source_url: str = Field(description="Прямая ссылка на источник")
    date_publication: datetime | None = Field(
        default=None,
        description="Дата публикации или обновления, только если она явно найдена",
    )


class ResearchResult(BaseModel):
    facts: list[ResearchFact]


@tool(name="call_researcher_agent", description="Вызвать агента исследователя")
async def call_researcher_agent(
    runtime: Runtime[Context, SrvCourseClient],
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
            ToolOutputCompressionMiddleware(),
            ToolCallLimitMiddleware(
                tool_limits={
                    "web_search": 4,
                    "browse_page": 5,
                    "knowledge_search": 5,
                    "save_knowledge": 4,
                }
            ),
        ],
    )
    result = await researcher_agent.invoke(
        messages=[{"role": "user", "content": schema.task}],
        schema=ResearchResult,
    )
    research = ResearchResult.model_validate(result.output)
    content = "\n\n".join(
        (
            f"Утверждение: {fact.claim}\n"
            f"Подтверждение: {fact.evidence}\n"
            f"Название источника: {fact.source_title}\n"
            f"Организация-издатель: {fact.source_organization or 'не указана'}\n"
            f"URL источника: {fact.source_url}\n"
            f"Дата публикации/обновления: "
            f"{fact.date_publication.isoformat() if fact.date_publication else 'не установлена'}"
        )
        for fact in research.facts
    )

    return {"role": "assistant", "content": content}


def reasoner_agent(runtime: Runtime[Context, SrvCourseClient]) -> LLMTextService:

    return LLMTextService(
        client=runtime.state,  # pyright: ignore[reportArgumentType]
        system_prompt=REASONER_PROMPT.format(prompt=runtime.context.prompt),
        tools={
            "call_researcher_agent": call_researcher_agent,
            "call_critique_agent": call_critique_agent,
        },
        middlewares=[
            ToolOutputCompressionMiddleware(),
            ToolCallLimitMiddleware(tool_limits={"call_researcher_agent": 2}),
        ],
        runtime=runtime,
    )
