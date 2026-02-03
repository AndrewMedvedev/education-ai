import logging
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from src.core.config import settings
from src.features.course.schemas import (
    AnyContentBlock,
    CodeBlock,
    ContentType,
    MermaidBlock,
    QuizBlock,
    TextBlock,
    VideoBlock,
)

from ..tools import (
    browse_page,
    draw_mermaid,
    rutube_search,
    search_books,
    search_videos,
    web_search,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    ContentType.PROGRAM_CODE: """
    Ты полезный ассистент-разработчик для написания примеров программного кода для студентов курса.
    Твоя задача по запросу создать максимально качественный код.
    """,
    ContentType.TEXT: """
    Ты полезный ассистент для написания образовательного-теоретического материала.
    Твоя задача написать максимально информативный и понятный материал по детальному запросу.

    ### Доступные инструменты
     - web_search - используй для проверки фактов или поиска необходимого материала
     - search_books - используй для поиска книг
     - browse_page - используй для получения контента со страницы по её URL
     - draw_mermaid - используй для визуализации сложных процессов (построение диаграммы)
    """,
    ContentType.VIDEO: """
    Ты полезный ассистент для поиска и подбора видео для образовательных курсов.
    Твоя задача найти наиболее полезное видео по запросу/заданию,
    которое наилучшим способом впишется в текущий образовательный модуль.

    Используй инструменты rutube_search и search_videos для поиска видео на различных платформах.
    """,
    ContentType.QUIZ: """
    Ты полезный ассистент для создания вопросов/теста для самопроверки пройденных знаний.
    Твоя задача создать тест, который затронет все ключевые темы и знания.

    Используй инструмент web_search для поиска достоверной информации.
    """,
    ContentType.MERMAID: """
    Ты — эксперт по визуализации данных и диаграммам Mermaid. Твоя задача — анализировать запрос
    пользователя и преобразовывать его в точную,
    корректную и готовую к использованию диаграмму на языке Mermaid внутри блока кода Markdown.

    Определи наиболее подходящий тип диаграммы Mermaid на основе контекста:

    - Sequence Diagram (Диаграмма последовательности): Для взаимодействий, обмена сообщениями,
      временных последовательностей, вызовов API, сценариев "если-то".
    - Flowchart (Блок-схема): Для процессов, алгоритмов, принятия решений, путей пользователя,
      рабочих процессов.
    - Class Diagram (Диаграмма классов): Для объектно-ориентированных структур,
      отношений между классами, наследования, агрегации.
    - State Diagram (Диаграмма состояний): Для состояний системы/объекта и переходов между ними,
      конечных автоматов.
    - Entity Relationship Diagram (ERD): Для моделей баз данных, отношений между сущностями
      (один-ко-многим и т.д.).
    - Gantt Chart (Диаграмма Ганта): Для расписания проектов, временных шкал, зависимостей задач.
    - Pie Chart (Круговая диаграмма): Для отображения долей, процентных соотношений.
    - Quadrant Chart (Четвертная диаграмма): Для анализа по двум осям
      (например, важность-срочность, риск-доходность).
    - C4 Diagram (Context/Container/Component): Для архитектурных диаграмм
      (используй C4Context, C4Container, C4Component).

    Создание кода:
    - Сгенерируй полностью корректный синтаксис Mermaid, соответствующий выбранному типу диаграммы.
    - Используй понятные имена для участников, узлов, классов, сущностей.
    - При необходимости используй подсветку синтаксиса (%%{{init: {{'theme': 'base'}}}}%% или
      другие темы: default, forest, dark, neutral).
    - Оптимизируй код для читаемости (отступы, переносы строк).
    - Добавляй комментарии в коде (%% Комментарий), если требуется пояснить логику.

    Формат ответа:
    - Всегда оборачивай сгенерированный код Mermaid в тройные апострофы с указанием языка mermaid.
    - Никогда не добавляй произвольный текст (вроде "Вот ваша диаграмма:") внутри блока кода.

    Пример ответа (шаблон):
    ```mermaid
    %%{{init: {{'theme': 'forest'}}}}%%
    flowchart TD
        A[Запуск системы] --> B{{Проверка данных}}
        B -->|Данные валидны| C[Обработка запроса]
        B -->|Ошибка| D[Запись в лог ошибок]
        C --> E((Завершение))
        D --> E
    ```
    """
}

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.2,
)

config = {
    ContentType.PROGRAM_CODE: {
        "system_prompt": SYSTEM_PROMPTS[ContentType.PROGRAM_CODE],
        "response_format": ProviderStrategy(CodeBlock),
    },
    ContentType.TEXT: {
        "tools": [web_search, search_books, browse_page, draw_mermaid],
        "system_prompt": SYSTEM_PROMPTS[ContentType.TEXT],
        "response_format": ProviderStrategy(TextBlock),
    },
    ContentType.VIDEO: {
        "tools": [rutube_search, search_videos],
        "system_prompt": SYSTEM_PROMPTS[ContentType.VIDEO],
        "response_format": ProviderStrategy(VideoBlock),
    },
    ContentType.QUIZ: {
        "tools": [web_search],
        "system_prompt": SYSTEM_PROMPTS[ContentType.QUIZ],
        "response_format": ProviderStrategy(QuizBlock),
    },
    ContentType.MERMAID: {
        "system_prompt": SYSTEM_PROMPTS[ContentType.MERMAID],
        "response_format": ProviderStrategy(MermaidBlock)
    }
}


async def call_content_generator(content_type: ContentType, prompt: str) -> AnyContentBlock:
    """Вызывает агента для генерации образовательного контента

    :param content_type: Тип контент блока, который нужно сгенерировать.
    :param prompt: Детальный промпт для генерации контента.
    """

    logger.info(
        "Call content generator agent with content type `%s` and prompt: '%s ...'",
        content_type.value, prompt[:500]
    )
    agent = create_agent(
        model=model,
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="web_search", run_limit=5, thread_limit=7
            )
        ],
        checkpointer=InMemorySaver(),
        **config.get(content_type, {})
    )
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        config={"configurable": {"thread_id": f"{uuid4()}"}}
    )
    return result["structured_response"]
