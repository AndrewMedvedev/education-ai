from typing import Any

import asyncio
import logging

import aiohttp
from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..intergrations import yandex_search_api
from ..services import crawler as crawler_service
from ..settings import PROMPTS_DIR, settings

logger = logging.getLogger(__name__)


async def search_in_rutube(query: str, videos_count: int = 10) -> list[dict[str, Any]]:
    logger.info("Calling `rutube_search` tool with query: `%s`", query)
    async with (
        aiohttp.ClientSession(base_url="https://rutube.ru/api/") as session,
        session.get(url="search/video", params={"query": query}) as response,
    ):
        data = await response.json()
    return [
        {
            "title": result["title"],
            "description": result["description"],
            "author_name": result["author"]["name"],
            "video_url": result["video_url"],
            "duration": result["duration"],
            "published_at": result["publication_ts"],
        }
        for result in data["results"][:videos_count]
    ]


@tool(parse_docstring=True)
def rutube_search(query: str, videos_count: int = 10) -> list[dict[str, Any]]:
    """Выполняет поиск видео в RuTube.

    Args:
        query: Запрос для поиска видео.
        videos_count: Количество видео которое нужно вернуть.
    """

    return asyncio.run(search_in_rutube(query, videos_count))


@tool(parse_docstring=True)
def web_search(query: str) -> list[dict[str, Any]]:
    """Выполняет поиск информации в интернете.

    Args:
        query: Поисковый запрос.
    """

    logger.info("Calling `web_search` tool with query: `%s`", query)
    return asyncio.run(yandex_search_api.search_async(query))


@tool(parse_docstring=True)
def browse_link(link: str) -> str:
    """Просматривает WEB-страницу по ссылке.

    Args:
        link: Ссылка на страницу.
    """

    logger.info("Calling `browse_link` tool with link: `%s`", link)
    try:
        return asyncio.run(crawler_service.crawl_web_page(link))
    except Exception:
        return "Не получилось загрузить страницу"


@tool(parse_docstring=True)
def draw_mermaid_diagram(prompt: str) -> str:
    """Рисует Mermaid диаграмму по твоему подробному запросу.

    Args:
        prompt: Твоё ТЗ для генерации диаграммы.
    """

    logger.info("Calling `draw_mermaid_diagram` tool with prompt: `%s`", prompt)
    model = ChatOpenAI(
        api_key=settings.yandexcloud.apikey,
        model=settings.yandexcloud.aliceai_llm,
        base_url=settings.yandexcloud.base_url,
        temperature=0.3,
        max_retries=3
    )
    system_prompt = (PROMPTS_DIR / "mermaid_artist.md").read_text(encoding="utf-8")
    chain = (
            ChatPromptTemplate.from_messages([("system", system_prompt)])
            | model
            | StrOutputParser()
    )
    return chain.invoke({"messages": [("human", prompt)]})


@tool(parse_docstring=True)
def write_code(language: str, prompt: str) -> str:
    """Инструмент для написания программного кода.

    Args:
        language: Язык программирования, на котором нужно написать код.
        prompt: Запрос для написания кода.
    """

    logger.info(
        "Calling `write_code` tool with language `%s` by prompt: `%s`",
        language, prompt
    )
    model = ChatOpenAI(
        api_key=settings.yandexcloud.apikey,
        model=settings.yandexcloud.qwen3_235b,
        base_url=settings.yandexcloud.base_url,
        temperature=0.2,
        max_tokens=3000,
        max_retries=3,
    )
    system_prompt = (PROMPTS_DIR / "code_writer.md").read_text(encoding="utf-8")
    chain = ChatPromptTemplate.from_template(system_prompt) | model | StrOutputParser()
    return chain.invoke({"language": language, "prompt": prompt})


content_block_generator_tools = [
    rutube_search, web_search, browse_link, draw_mermaid_diagram, write_code
]
