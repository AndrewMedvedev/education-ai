# Суб агент - практик

import logging
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from src.core.entities.course import (
    AnyAssignment,
    AssignmentType,
    FileUploadAssignment,
    GitHubAssignment,
    TestAssignment,
)
from src.settings import settings

from ..schemas import CourseContext
from ..tools import knowledge_search

logger = logging.getLogger(__name__)

# Системные промпты для генерации разных типов практических заданий
SYSTEM_PROMPTS = {
    AssignmentType.TEST: """\
    Ты — опытный методист, создающий тесты для проверки знаний студентов.
    Твоя задача — на основе промпта преподавателя и материала курса создать качественный тест.

    ### Правила создания теста:
     1. **Количество вопросов**: 7–10, если не указано иное в промпте.
     2. **Типы вопросов**: предпочтительно открытые вопросы или вопросы с развёрнутым ответом.
        Избегай тривиальных «да/нет» вопросов.
     3. **Каждый вопрос должен**:
        - Проверять понимание, а не просто запоминание.
        - Иметь чёткую формулировку.
        - Содержать варианты ответов (если это тест с выбором) — от 3 до 5 вариантов.
        - Указывать правильные ответы (индексы) и баллы за вопрос (points).
     4. **Разнообразие**: вопросы должны покрывать разные уровни таксономии Блума:
        - понимание (объяснить, описать)
        - применение (решить, выбрать правильный пример)
        - анализ (сравнить, найти ошибку)

     ### Инструкция по использованию инструментов:
      - **knowledge_search** — вызывай, если нужно найти актуальные примеры кода, определения,
        или уточнить термины, которые не понятны из промпта.
      - Формируй запрос максимально конкретно: например, "примеры нарушения YAGNI в Python",
        а не просто "YAGNI".
    """,
    AssignmentType.FILE_UPLOAD: """\
    Ты — эксперт по созданию практических заданий с загрузкой файлов.
    Твоя задача — на основе промпта от преподавателя разработать детальное задание.

    ### Структура задания:
    1. **task** — чёткое описание того, что нужно сделать студенту. Включи:
     - Цель задания
     - Контекст (например, "Дан код приложения...")
     - Конкретные шаги выполнения
     - Что должно быть в итоговом файле
    2. **allowed_extensions** — список разрешённых расширений (например, [".pdf", ".docx", ".py"]).
       Если задание подразумевает любой текстовый файл, оставь ["*"].
    3. **submission_instructions** — инструкции по оформлению: название файла, структура отчёта,
       требования к коду (PEP8, комментарии), что обязательно включить.

    ### Требования к качеству:
     - Задание должно быть выполнимо за разумное время (указанное в промпте).
     - Чётко разделяй обязательные и опциональные части.
    """,
    AssignmentType.GITHUB: """\
    Ты — специалист по созданию заданий, выполняемых в GitHub.
    Твоя задача — на основе промпта разработать детальное задание.

    ### Структура задания:
     1. **repository_task** — описание того, что студент должен сделать в репозитории:
        - Создать новый репозиторий или использовать существующий?
        - Какие файлы создать/изменить?
        - Какая функциональность должна быть реализована?
        - Требования к коду, тестам, документации.
    2. **repository_rules** — правила оформления репозитория:
        - Структура папок (например, `/tg_bot`, `/tests`, `/docs`)
        - Именование веток, коммитов (conventional commits)
        - Наличие README, лицензии, .gitignore
        - Требования к пул-реквестам (если применимо)
    3. **required_branch** — основная ветка для проверки (обычно main/master).

    ### Требования к качеству:
     - Задание должно быть выполнимо в рамках одного репозитория.
     - Указывай конкретные имена файлов и функции, которые нужно реализовать.
     - Предусмотри критерии оценки: что проверяющий будет смотреть в первую очередь.
    - Если задание командное, опиши роли и взаимодействие через GitHub.

    ### Использование инструментов:
     - **knowledge_search** — вызывай для поиска информации касаемо предметной области курса.
     - Старайся минимизировать вызовы: максимум 1–2, если промпт неполон.

    Пример хорошего repository_task (не для вывода):
    "Создайте публичный репозиторий на GitHub с названием 'weather-api'.
    Реализуйте простое REST API на FastAPI, которое возвращает погоду по названию города
    (используйте бесплатный API, например, OpenWeatherMap). API должен иметь:
     - эндпоинт GET /weather?city={city}
     - обработку ошибок (город не найден, таймаут)
     - минимум 2 unit-теста на ключевые функции.
    В README опишите установку, запуск и примеры запросов."
    """
}

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.2,
)

config = {
    AssignmentType.TEST: {
        "tools": [knowledge_search],
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.TEST],
        "response_format": ProviderStrategy(TestAssignment),
    },
    AssignmentType.FILE_UPLOAD: {
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.FILE_UPLOAD],
        "response_format": ProviderStrategy(FileUploadAssignment),
    },
    AssignmentType.GITHUB: {
        "tools": [knowledge_search],
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.GITHUB],
        "response_format": ProviderStrategy(GitHubAssignment),
    },
}


async def call_practice_agent(
        assignment_type: AssignmentType, prompt: str, context: CourseContext
) -> AnyAssignment:
    """Вызывает агента - генератора практических заданий для модуля

    :param assignment_type: Тип практического задания.
    :param prompt: Детальный промпт для генерации задания.
    :param context: Контекстная информация преподавателя.
    """

    logger.info("Calling practice agent for assignment type `%s` ...", assignment_type.value)
    agent = create_agent(
        model=model,
        context_schema=CourseContext,
        checkpointer=InMemorySaver(),
        **config.get(assignment_type, {})
    )
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        context=context,
        config={"configurable": {"thread_id": f"{uuid4()}"}}
    )
    return result["structured_response"]
