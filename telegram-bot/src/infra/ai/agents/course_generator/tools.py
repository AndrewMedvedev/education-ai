from typing import Literal

import logging

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field, NonNegativeFloat

from ... import rag
from .schemas import CourseContext

logger = logging.getLogger(__name__)


class SaveKnowledgeInput(BaseModel):
    """Аргументы для сохранения знаний"""

    category: Literal["materials", "web_research", "theory"] = Field(
        default="web_research",
        description="""\
            Тип знаний:
             - materials - информация полученная из материалов преподавателя
             - web_research - информация полученная в ходе изучения предметной области
             - theory - сгенерированный теоретический материал уже созданного курса
            """,
    )
    source: str = Field(
        ...,
        description="Источник полученных знаний, например имя файла, URL адрес, название ресурса",
    )
    text: str = Field(..., description="Полезная информация, которую необходимо запомнить")
    score: NonNegativeFloat = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Насколько полезна информация, где 1 максимально релевантная информация",
    )


@tool(
    "save_knowledge",
    description="Сохраняет информацию в базу знаний курса",
    args_schema=SaveKnowledgeInput,
)
def save_knowledge(
        runtime: ToolRuntime[CourseContext],
        source: str,
        text: str,
        score: float,
        category: Literal["materials", "web_research", "theory"] = "web_research",
) -> None:
    logger.info(
        "Saving `%s` knowledge from %s, score %s%%, text: '%s ...'",
        category, source, score, text[:150]
    )
    rag.indexing(
        text=text,
        metadata={
            "tenant_id": str(runtime.context.course_id),
            "source": source,
            "category": category,
            "score": score,
        }
    )


class KnowledgeSearchInput(BaseModel):
    search_query: str = Field(description="Запрос для поиска информации")
    category: Literal[
        "materials",
        "web_research",
        "theory"
    ] | None = Field(default=None, description="Тип информации, который нужно найти")


@tool(
    "knowledge_search",
    description="Поиск информации в базе знаний курса",
    args_schema=KnowledgeSearchInput,
)
def knowledge_search(
        runtime: ToolRuntime[CourseContext],
        search_query: str,
        category: Literal["materials", "web_research", "theory"] | None = None
) -> str:
    meta_filter = {}
    tenant_filter = {"tenant_id": str(runtime.context.course_id)}
    if category is not None:
        logger.info(
            "Searching knowledge by category - `%s` and query: '%s ...'",
            category, search_query[:100]
        )
        meta_filter["$and"] = [tenant_filter, {"category": category}]
    else:
        logger.info("Searching knowledge by query `%s`", search_query[:100])
        meta_filter.update(**tenant_filter)
    docs = rag.retrieve(search_query, metadata_filter=meta_filter)
    return "\n\n".join(docs)
