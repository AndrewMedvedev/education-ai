from typing import Any

import logging

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, PositiveInt

from src.core.config import settings
from src.crawler import crawl_page_content
from src.intergrations import rutube_api, yandex_search_api

from .prompts import CODE_WRITER_PROMPT, MERMAID_ARTIST_PROMPT

logger = logging.getLogger(__name__)


class RuTubeSearchInput(BaseModel):
    """Входные аргументы для поиска видео в RuTube"""

    search_query: str = Field(description="Запрос для поиска видео")
    videos_count: PositiveInt = Field(
        default=10, description="Количество видео, которое нужно найти"
    )


@tool(
    "rutube_search",
    description="Выполняет поиск видео на платформе RuTube",
    args_schema=RuTubeSearchInput
)
async def rutube_search(search_query: str, videos_count: int = 10) -> list[dict[str, Any]]:
    return await rutube_api.search_videos(search_query, videos_count)


class WebSearchInput(BaseModel):
    search_query: str = Field(description="Поисковый запрос")


@tool(
    "web_search",
    description="""
    Выполняет поиск в Яндекс.
    Возвращает список найденных страниц с заголовками, URL и кратким описанием.
    Подходит для получения актуальной информации из интернета.""",
    args_schema=WebSearchInput,
)
async def web_search(search_query: str) -> list[dict[str, Any]]:
    return await yandex_search_api.search_async(search_query)


class BrowseLinkInput(BaseModel):
    link: str = Field(description="Ссылка на страницу с которой нужно получить контент")


@tool(
    "browse_page",
    description="Открывает WEB-страницу и получает её контент в формате Markdown",
    args_schema=BrowseLinkInput,
)
async def browse_page(link: str) -> str:
    return await crawl_page_content(link)


class MermaidInput(BaseModel):
    prompt: str = Field(description="Промпт для генерации mermaid диаграммы")


@tool(
    "draw_mermaid",
    description="Рисует mermaid диаграмму по описанию, возвращает Markdown с mermaid-блоком",
    args_schema=MermaidInput,
)
async def draw_mermaid(prompt: str) -> str:
    mermaid_agent = create_agent(
        model=ChatOpenAI(
            api_key=settings.yandexcloud.api_key,
            model=settings.yandexcloud.qwen3_235b,
            base_url=settings.yandexcloud.base_url,
            temperature=0.3,
        ),
        system_prompt=MERMAID_ARTIST_PROMPT,
    )
    result = await mermaid_agent.ainvoke({"messages": [("human", prompt)]})
    return result["messages"][-1].content


class CodeWriterInput(BaseModel):
    language: str = Field(description="Язык программирования на котором нужно написать код")
    prompt: str = Field(description="Твоё техническое задание или запрос для написания кода")


@tool(
    "write_code",
    description="Пишет качественный программный код",
    args_schema=CodeWriterInput,
)
async def write_code(language: str, prompt: str) -> str:
    model = ChatOpenAI(
        api_key=settings.yandexcloud.api_key,
        model=settings.yandexcloud.qwen3_235b,
        base_url=settings.yandexcloud.base_url,
        temperature=0.2,
        max_tokens=3000,
        max_retries=3,
    )
    chain = ChatPromptTemplate.from_template(CODE_WRITER_PROMPT) | model | StrOutputParser()
    return await chain.ainvoke({"language": language, "prompt": prompt})
