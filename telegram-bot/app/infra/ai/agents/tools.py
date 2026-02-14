from typing import Any

import logging

from ddgs import DDGS
from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.infra.intergrations import rutube, yandex_web_search
from app.settings import settings
from app.utils.browser_automation import get_page_text

from .prompts import CODER_PROMPT, MERMAID_PROMPT

logger = logging.getLogger(__name__)


class SearchInput(BaseModel):
    """Входные аргументы для поиска видео в RuTube"""

    search_query: str = Field(description="Запрос для поиска")


@tool(
    "rutube_search",
    description="Выполняет поиск видео на платформе RuTube",
    args_schema=SearchInput
)
async def rutube_search(search_query: str) -> list[dict[str, Any]]:
    return await rutube.search_videos(search_query)


@tool(
    "yandex_search",
    description="""\
    Выполняет поиск в Яндекс.
    Возвращает список найденных страниц с заголовками, URL и кратким описанием.
    Подходит для получения актуальной информации из интернета.
    Используй этот инструмент экономно.
    """,
    args_schema=SearchInput,
)
async def yandex_search(search_query: str) -> list[dict[str, Any]]:
    return await yandex_web_search.search_async(search_query)


class BrowsePageInput(BaseModel):
    link: str = Field(description="Ссылка на страницу с которой нужно получить контент")


@tool(
    "browse_page",
    description="Открывает WEB-страницу и получает её контент в формате Markdown",
    args_schema=BrowsePageInput,
)
async def browse_page(link: str) -> str:
    return await get_page_text(link)


class MermaidInput(BaseModel):
    prompt: str = Field(description="Промпт для генерации mermaid диаграммы")


@tool(
    "draw_mermaid",
    description="Рисует mermaid диаграмму по описанию, возвращает Markdown с mermaid-блоком",
    args_schema=MermaidInput,
)
async def draw_mermaid(prompt: str) -> str:
    model = ChatOpenAI(
        api_key=settings.yandexcloud.api_key,
        model=settings.yandexcloud.qwen3_235b,
        base_url=settings.yandexcloud.base_url,
        temperature=0.3,
     )
    chain = (
        ChatPromptTemplate.from_messages([
            ("system", MERMAID_PROMPT), MessagesPlaceholder("messages")
        ])
        | model
        | StrOutputParser()
    )
    return await chain.ainvoke({"messages": [("human", prompt)]})


class CoderInput(BaseModel):
    language: str = Field(description="Язык программирования на котором нужно написать код")
    prompt: str = Field(description="Твоё техническое задание или запрос для написания кода")


@tool(
    "write_code",
    description="Пишет качественный программный код",
    args_schema=CoderInput,
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
    chain = ChatPromptTemplate.from_template(CODER_PROMPT) | model | StrOutputParser()
    return await chain.ainvoke({"language": language, "prompt": prompt})


@tool(
    "search_videos",
    description="Выполняет поиск видео в интернете с разных платформ",
    args_schema=SearchInput,
)
def search_videos(search_query: str) -> list[dict[str, Any]]:
    return DDGS().videos(search_query, region="ru-ru", max_results=10)


@tool(
    "web_search",
    description="""\
    Выполняет поиск в интернете.
    Возвращает список найденных страниц с заголовками, URL и кратким описанием.
    Подходит для получения актуальной информации из интернета.
    Используй этот инструмент экономно.
    """,
    args_schema=SearchInput
)
def web_search(search_query: str) -> list[dict[str, Any]]:
    return DDGS().text(search_query, region="ru-ru", max_results=10)


@tool(
    "search_books",
    description="Выполняет поиск книг в интернете",
    args_schema=SearchInput,
)
def search_books(search_query: str) -> list[dict[str, Any]]:
    return DDGS().books(search_query, region="ru-ru", max_results=10)
