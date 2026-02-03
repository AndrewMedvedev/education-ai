from typing import NotRequired

import logging

from langchain.agents import AgentState, create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END
from langgraph.types import Command
from pydantic import BaseModel, Field, PositiveInt

from src.core.config import settings
from src.rag import get_rag_pipeline

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
    max_retries=3
)

SYSTEM_PROMPT = """\
Ты — профессиональный агент интервьюер для создания современных образовательных курсов.
Твоя главная цель провести короткое и максимально полезное интервью, после которого у других
агентов будет достаточно структурированной информации для создания курса.

## Доступные инструменты
 - search_materials - поиск по уже существующим материалам преподавателя
   (лекции, статьи, слайды, заметки и т.д.), используй его для анализа материалов
 - complete_interview - завершает интервью и передаёт информацию следующим агентам

## Правиле проведения интервью
1. Максимум 4 - 5 самых необходимых вопроса (те вопросы,
без ответов на которые нельзя построить качественный курс)
2. Если у преподавателя уже есть качественные материалы → используй search_materials
и задавай меньше вопросов
3. Структурируй интервью вокруг 4–5 ключевых блоков (не обязательно все):
    • Целевая аудитория и её реальный уровень
    • Продолжительность и размер курса
    • Самые важные 5–8 тем / блоков / навыков, которые должны остаться после курса
    • Последовательность и логика подачи (что должно идти строго перед чем)
    • Самые частые заблуждения / ошибки учеников
    • Практические примеры, кейсы, задачи, которые "заходят" лучше всего
    • (опционально) — как быстро проверить, что человек действительно понял тему
4. Приводи примеры того, как можно ответить на вопрос, чтобы преподаватель понимал
как оформить свой ответ

Начинай интервью сразу с первого осмысленного вопроса после короткого представления
(1–2 предложения максимум).
Если есть доступ к материалам эксперта — сначала сделай поиск
через search_materials и адаптируй вопросы.
"""

SUMMARY_PROMPT = """\
Ты — агент-экстрактор ключевой информации для создания образовательного курса.
Твоя единственная задача — проанализировать историю интервью с экспертом и извлечь **только самые важные, конкретные и полезные факты**, которые напрямую помогут следующим агентам построить сильный курс.

Правила извлечения (строго соблюдай):
• Выбрасывай всё лишнее: любезности, повторения, общие фразы, философию, истории «из жизни», неконкретные рассуждения.
• Оставляй только факты, мнения эксперта и примеры, которые можно прямо использовать в структуре курса.
• Формулируй кратко, чётко, без воды. Предпочитай списки, таблицы, нумерованные/маркированные структуры.
• Не интерпретируй и не додумывай — только то, что эксперт явно сказал.
• Если чего-то важного не спросили → отмечай это как «не получено от эксперта».

Обязательная структура результата (выводи именно в таком виде, без вступлений и заключений):

## 1. Название курса
 - Название, которое указал преподаватель

## 2. Целевая аудитория (самое точное описание, которое дал эксперт)
- Возраст / опыт / бэкграунд:
- Главные боли / проблемы / мотивации:
- Что уже умеют (реальный стартовый уровень):
- Что категорически НЕ умеют / не понимают:

## 3. Продолжительность и примерный размер курса
 - Количество академических часов или количество модулей

## 4. Главные учебные цели курса (5–8 самых важных)
Нумерованный список в формате:
1. Уметь … (конкретный навык / результат)
2. Понять … (ключевое понятие / принцип)
...

## 5. Рекомендуемая структура курса (блоки / модули)
Пронумерованный список модулей в той последовательности, которую назвал эксперт.
Если эксперт дал чёткую логику «что перед чем должно идти» — обязательно укажи это.

## 6. Ключевые темы / подтемы (то, без чего курс невозможен)
- Модуль 1: …
  • подтема А
  • подтема Б
- Модуль 2: …

## 7. Самые частые заблуждения / типичные ошибки учеников
(список, каждый пункт — одно заблуждение + короткое объяснение, почему оно возникает)

## 8. Лучшие практические примеры / кейсы / задачи
(конкретные примеры, которые эксперт назвал удачными / «заходят» ученикам)

## 9. Способы проверки понимания (если упоминались)
- Задачи / тесты / вопросы / практические задания, которые эксперт считает показательными

## 10. Важные акценты / подводные камни / «ловушки» материала
(список того, на чём эксперт особенно настаивал)

## 11. Пропущенные важные блоки (чего не хватило в интервью)
Перечисли темы/вопросы, которые логично должны были быть, но эксперт о них почти ничего не сказал или сказал слишком общо.

## 12. Краткая выжимка «одним абзацем»
2–4 предложения — самое главное, что должен запомнить следующий агент.

Выводи результат **только** в указанной структуре.
Не пиши никаких предисловий, послесловий, пояснений «я думаю» или «по моему мнению».
Если какой-то раздел пустой или почти пустой — пиши «не получено от эксперта» или «эксперт не дал конкретики».

Начинай сразу с заголовка ## 1. Название курса
"""  # noqa: E501


class UserContext(BaseModel):
    user_id: PositiveInt


class State(AgentState):
    """Состояние интервью"""

    summary: NotRequired[str]  # Основные выводы и инсайты полученные из интервью


class SearchInput(BaseModel):
    """Входные параметры для поиска по прикреплённым материалам"""

    search_query: str = Field(description="Запрос для поиска")


@tool(
    "search_materials",
    description="Выполняет поиск по материалам преподавателя",
    args_schema=SearchInput,
)
def search_materials(runtime: ToolRuntime[UserContext, State], search_query: str) -> str:
    index_name = f"materials-{runtime.context.user_id}-index"
    rag_pipeline = get_rag_pipeline(index_name=index_name)
    documents = rag_pipeline.retrieve(search_query)
    return "\n\n".join(documents)


@tool(
    "complete_interview",
    description="Завершает интервью для передачи данных следующему агенту"
)
async def complete_interview(runtime: ToolRuntime[UserContext, State]) -> Command:
    logger.info("Finishing interview session for teacher `%s`", runtime.context.user_id)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARY_PROMPT), MessagesPlaceholder("messages"),
    ])
    chain = prompt | model | StrOutputParser()
    logger.info(
        "Starting to summarize interview dialog with teacher `%s`",
        runtime.context.user_id
    )
    summary = await chain.ainvoke({"messages": [*runtime.state["messages"]]})
    tool_message = ToolMessage(content=summary, tool_call_id=runtime.tool_call_id)
    logger.info(
        "Interview complete successfully for user `%s`, interview summary: '%s ...'",
        runtime.context.user_id, summary[:500]
    )
    return Command(update={"messages": [tool_message], "summary": summary}, goto=END)


interviewer_agent = create_agent(
    model=model,
    tools=[search_materials, complete_interview],
    context_schema=UserContext,
    state_schema=State,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),
)
