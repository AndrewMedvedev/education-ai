from typing import Any

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps

from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, PositiveInt

from ..intergrations import rutube_api, yandex_search_api
from ..services import crawler as crawler_service
from ..settings import PROMPTS_DIR, settings

logger = logging.getLogger(__name__)

RESULT_PREVIEW_CHARS = 200


def log_tool_call(tool_name: str | None = None):
    """Декоратор для логирования вызовов инструментов"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tool_id = tool_name or func.__name__
            start_time = time.time()
            logger.info(
                "🛠️ TOOL CALL START: %s", tool_id,
                extra={
                    "tool": tool_id,
                    "input_args": args,
                    "input_kwargs": kwargs,
                    "timestamp": start_time,
                },
            )
            try:
                result = func(*args, **kwargs)
                execution_time = round(time.time() - start_time, 2)
                result_preview = (
                    str(result)[:RESULT_PREVIEW_CHARS] + "..."
                    if len(str(result)) > RESULT_PREVIEW_CHARS
                    else str(result)
                )
                logger.info(
                    "✅ TOOL CALL SUCCESS: %s (%s s)", tool_id, execution_time,
                    extra={
                        "tool": tool_id,
                        "execution_time": execution_time,
                        "result_preview": result_preview,
                        "result_type": type(result).__name__,
                        "result_length": len(str(result)) if hasattr(result, "__len__") else None,
                    },
                )
            except Exception as e:
                execution_time = round(time.time() - start_time, 2)
                logger.exception(
                    "❌ TOOL CALL FAILED: %s (%s s)", tool_id, execution_time,
                    extra={
                        "tool": tool_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "execution_time": execution_time,
                    },
                )
                raise
            else:
                return result
        return wrapper
    return decorator


class RuTubeSearchInput(BaseModel):
    """Входные аргументы для поиска видео в RuTube"""

    search_query: str = Field(description="Поисковый запрос")
    videos_count: PositiveInt = Field(
        default=10, description="Количество видео, которое нужно вернуть"
    )


@tool(
    "search_videos_in_rutube",
    description="Выполняет поиск видео на платформе RuTube",
    args_schema=RuTubeSearchInput
)
@log_tool_call("search_videos_in_rutube")
def rutube_search(search_query: str, videos_count: int = 10) -> list[dict[str, Any]]:
    """Выполняет поиск видео в RuTube."""

    return asyncio.run(rutube_api.search_videos(search_query, videos_count))


class WebSearchInput(BaseModel):
    search_query: str = Field(description="Поисковый запрос")


@tool(
    "web_search",
    description="""Выполняет поиск в Яндекс. Поисковик.
    Возвращает список найденных страниц с заголовками, URL и кратким описанием.
    Подходит для получения актуальной информации из интернета.""",
    args_schema=WebSearchInput,
)
@log_tool_call("web_search")
def web_search(search_query: str) -> list[dict[str, Any]]:
    """Выполняет поиск информации в интернете"""

    return asyncio.run(yandex_search_api.search_async(search_query))


class BrowseLinkInput(BaseModel):
    link: str = Field(description="Ссылка на страницу с которой нужно получить контент")


@tool(
    "browse_web_page",
    description="Открывает WEB-страницу и получает её контент в формате Markdown",
    args_schema=BrowseLinkInput,
)
@log_tool_call("browse_web_page")
def browse_link(link: str) -> str:
    """Просматривает WEB-страницу по ссылке"""

    try:
        return asyncio.run(crawler_service.crawl_web_page(link))
    except Exception:  # noqa: BLE001
        return "Не удалось открыть страницу"


class MermaidInput(BaseModel):
    prompt: str = Field(description="ТЗ для генерации mermaid диаграммы")


@tool(
    "draw_mermaid_diagram",
    description="Рисует mermaid диаграмму по описанию, возвращает Markdown с mermaid-блоком",
    args_schema=MermaidInput,
)
@log_tool_call("draw_mermaid_diagram")
def draw_mermaid_diagram(prompt: str) -> str:
    """Рисует Mermaid диаграмму по твоему подробному запросу"""

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


class CodeWriterInput(BaseModel):
    language: str = Field(description="Язык программирования на котором нужно написать код")
    prompt: str = Field(description="Твоё техническое задание или запрос для написания кода")


@tool(
    "write_program_code",
    description="Пишет качественный программный код",
    args_schema=CodeWriterInput,
)
@log_tool_call("write_program_code")
def write_code(language: str, prompt: str) -> str:
    """Инструмент для написания программного кода"""

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


# Инструменты для выполнения задач
task_executor_tools = [
    rutube_search, web_search, browse_link
]
# Инструменты для создания контент блока
response_compiler_tools = [
    rutube_search, web_search, browse_link, draw_mermaid_diagram, write_code
]
