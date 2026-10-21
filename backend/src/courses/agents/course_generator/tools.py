from typing import Any, Literal

import hashlib
import logging
from datetime import UTC, datetime

from ddgs import DDGS
from pydantic import BaseModel, Field, NonNegativeFloat

from src.core.qdrant import qdrant_client
from src.courses.agents.course_generator.few_shots import (
    COURSE_STRUCTURE_FEW_SHOT,
    LESSON_STRUCTURE_FEW_SHOT,
    MODULE_STRUCTURE_FEW_SHOT,
)
from src.courses.agents.course_generator.subagents.prompts import (
    COURSE_STRUCTURE_PROMPT,
    LESSON_STRUCTURE_PROMPT,
    MODULE_STRUCTURE_PROMPT,
    CourseStructure,
    LessonStructure,
    ModuleStructure,
)
from src.courses.agents.tools import State
from src.courses.dependencies.base import splitter
from src.courses.infra.database.repos.vector_repo import QdrantRepository
from src.courses.utils.browser_automation import get_page_text
from src.llm_service import Runtime, tool
from src.llm_service.services import LLMTextService

from ..schemas import CourseContext

logger = logging.getLogger(__name__)


class SaveKnowledgeInput(BaseModel):
    category: Literal["data", "web_research", "theory"] = "web_research"

    claim: str = Field(description="Проверенное утверждение")
    evidence: str = Field(description="Подтверждение утверждения, полученное из источника")

    source_title: str = Field(description="Название документа или страницы")
    source_organization: str = Field(description="Организация — автор или издатель источника")
    source_url: str = Field(description="URL, полученный от инструмента")
    date_publication: datetime | None = Field(
        default=None,
        description="Дата публикации или обновления, если она найдена",
    )

    quality_score: NonNegativeFloat | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Оценка полезности записи; не является оценкой релевантности поиска",
    )


@tool(name="save_knowledge", description="Сохраняет проверенное знание курса")
async def save_knowledge(
    runtime: Runtime[CourseContext, list[dict[str, Any]]],
    schema: SaveKnowledgeInput,
) -> str:
    source_identity = schema.source_url.strip()
    if not source_identity:
        return "Знание не сохранено: отсутствует URL источника."

    normalized_claim = " ".join(schema.claim.split())
    document_id = hashlib.sha256(
        (
            f"{runtime.context.course_id}|{schema.category}|{source_identity}|{normalized_claim}"
        ).encode()
    ).hexdigest()

    indexed_text = "\n".join(
        [
            f"Утверждение: {schema.claim}",
            f"Подтверждение: {schema.evidence}",
            f"Источник: {schema.source_title}",
            f"Организация: {schema.source_organization}",
            f"URL: {schema.source_url}",
            (
                f"Дата публикации/обновления: {schema.date_publication.isoformat()}"
                if schema.date_publication
                else "Дата публикации/обновления: не установлена"
            ),
        ]
    )

    metadata = {
        "course_id": str(runtime.context.course_id),
        "category": schema.category,
        "document_id": document_id,
        "claim": schema.claim,
        "evidence": schema.evidence,
        "source_title": schema.source_title,
        "source_organization": schema.source_organization,
        "source_url": schema.source_url,
        "date_publication": (
            schema.date_publication.isoformat() if schema.date_publication else None
        ),
        "date_indexed": datetime.now(UTC).isoformat(),
        "quality_score": schema.quality_score,
    }

    await QdrantRepository(client=qdrant_client, splitter=splitter).create(
        text=indexed_text,
        metadata=metadata,
        document_id=document_id,
    )

    return "Данные успешно сохранены в базу знаний курса"


class KnowledgeSearchInput(BaseModel):
    search_query: str = Field(description="Запрос для поиска информации")
    category: Literal["data", "web_research", "theory"] | None = Field(
        default=None, description="Тип информации, который нужно найти"
    )


@tool(
    name="knowledge_search",
    description="Поиск информации в базе знаний курса",
)
async def knowledge_search(
    runtime: Runtime[CourseContext, list[dict[str, Any]]],
    schema: KnowledgeSearchInput,
) -> str:
    meta_filter = {"course_id": str(runtime.context.course_id)}
    if schema.category is not None:
        logger.info(
            "Searching knowledge by category - `%s` and query: '%s ...'",
            schema.category,
            schema.search_query[:100],
        )
        meta_filter["category"] = schema.category
    else:
        logger.info("Searching knowledge by query `%s`", schema.search_query[:100])

    try:
        docs = await QdrantRepository(client=qdrant_client, splitter=splitter).read(
            query=schema.search_query, metadata_filters=meta_filter
        )
        if not docs:
            return (
                f"По запросу '{schema.search_query}' (категория: {schema.category or 'любая'}) "
                "в базе знаний ничего не найдено. Не повторяй этот запрос с похожей "
                "формулировкой — либо измени категорию, либо переходи к следующему "
                "шагу плана без этой информации."
            )
        return "\n\n".join(docs)
    except Exception:
        logger.exception("Knowledge search failed for query %r", schema.search_query)

        return f"Поиск по запросу {schema.search_query}, завершился непредвиденной ошибкой, не повторяй этот запрос"  # noqa: E501


class SearchInput(BaseModel):
    """Входные аргументы для поиска видео в RuTube"""

    search_query: str = Field(description="Запрос для поиска")


class BrowsePageInput(BaseModel):
    link: str = Field(description="Ссылка на страницу с которой нужно получить контент")


@tool(
    name="browse_page",
    description="Открывает WEB-страницу и возвращает текст вместе с URL источника",
)
async def browse_page(schema: BrowsePageInput) -> dict[str, str]:
    page_text = await get_page_text(schema.link)
    return {"source": schema.link, "text": page_text}


@tool(
    name="web_search",
    description="""\
    Выполняет поиск в интернете.
    Возвращает список найденных страниц с заголовками, URL и кратким описанием.
    Подходит для получения актуальной информации из интернета.
    Используй этот инструмент экономно.
    """,
)
async def web_search(schema: SearchInput) -> list[dict[str, Any]]:
    return DDGS().text(schema.search_query, region="ru-ru", max_results=10)


class MaterialsInput(BaseModel):
    materials: str = Field(description="Собранные данные в ходе интервью с пользователем")


@tool(
    name="generate_course_structure",
    description="""\
    Создает структуру курса с примерной стоимостью в рублях.
    """,
)
async def generate_course_structure(
    schema: MaterialsInput,
    runtime: Runtime[CourseContext, State],
) -> dict[str, dict[str, Any] | str]:
    agent = LLMTextService(client=runtime.state.client, system_prompt=COURSE_STRUCTURE_PROMPT)  # pyright: ignore[reportOptionalMemberAccess]
    request = await agent.invoke(
        messages=[
            *COURSE_STRUCTURE_FEW_SHOT,
            {
                "role": "user",
                "content": schema.materials,
            },
        ],
        schema=CourseStructure,
    )
    result = CourseStructure.model_validate(request.output)

    return {
        "plan": result.model_dump(mode="json"),
        "cost": f"{len(result.module_descriptions) * 10 * 10 * 4} рублей",
    }


@tool(
    name="generate_module_structure",
    description="""\
    Создает структуру модуля с примерной стоимостью в рублях.
    """,
)
async def generate_module_structure(
    schema: MaterialsInput,
    runtime: Runtime[CourseContext, State],
) -> dict[str, dict[str, Any] | str]:
    agent = LLMTextService(client=runtime.state.client, system_prompt=MODULE_STRUCTURE_PROMPT)  # pyright: ignore[reportOptionalMemberAccess]
    request = await agent.invoke(
        messages=[
            *MODULE_STRUCTURE_FEW_SHOT,
            {
                "role": "user",
                "content": schema.materials,
            },
        ],
        schema=ModuleStructure,
    )
    result = ModuleStructure.model_validate(request.output)

    return {
        "plan": result.model_dump(mode="json"),
        "cost": f"{len(result.lessons_descriptions) * 10 * 4} рублей",
    }


@tool(
    name="generate_lesson_structure",
    description="""\
    Создает структуру урока с примерной стоимостью в рублях.
    """,
)
async def generate_lesson_structure(
    schema: MaterialsInput,
    runtime: Runtime[CourseContext, State],
) -> dict[str, dict[str, Any] | str]:
    agent = LLMTextService(client=runtime.state.client, system_prompt=LESSON_STRUCTURE_PROMPT)  # pyright: ignore[reportOptionalMemberAccess]
    request = await agent.invoke(
        messages=[
            *LESSON_STRUCTURE_FEW_SHOT,
            {
                "role": "user",
                "content": schema.materials,
            },
        ],
        schema=LessonStructure,
    )
    result = LessonStructure.model_validate(request.output)

    return {
        "plan": result.model_dump(mode="json"),
        "cost": f"{len(result.content_plan) * 4} рублей",
    }
