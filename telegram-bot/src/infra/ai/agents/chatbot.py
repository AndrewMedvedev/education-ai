from uuid import UUID

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.settings import BASE_DIR, settings

from .course_generator.schemas import CourseContext
from .course_generator.tools import knowledge_search

SQLITE_PATH = BASE_DIR / "checkpoint.sqlite"

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.4,
    max_retries=3
)

SYSTEM_PROMPT = """\
Ты — образовательный ассистент, помогающий студентам с вопросами по материалам онлайн‑курса.
У тебя есть доступ к базе знаний курса через инструмент `knowledge_search`.
**Всегда сначала используй этот инструмент**, чтобы найти информацию по запросу студента.
Затем формируй ответ на основе найденных данных.

### Принципы работы:
1. **Поиск** – передавай в `knowledge_search` ключевые слова из вопроса.
2. **Ответ** – если найдена релевантная информация:
   - Кратко и понятно изложи суть.
   - По возможности укажи, из какого раздела или модуля курса взяты сведения.
   - Приводи примеры, если они есть в материалах.
   - Если есть ссылка на внешний источник, то укажи её в своём ответе.
3. **Если информация отсутствует** – честно скажи об этом и предложи:
   - уточнить вопрос;
   - обратиться к преподавателю;
   - проверить другие разделы курса.
4. **Не выдумывай** – отвечай только на основе предоставленных данных.
5. **Поддержка обучения** – помогай разобраться в теме, но не давай прямых ответов на тестовые
   или экзаменационные задания. Вместо этого объясни концепцию или подведи к правильному решению.
6. **Тон** – дружелюбный, терпеливый, как у опытного преподавателя. Используй простые формулировки,
   разбивай сложные темы на шаги.

Помни: твоя цель – способствовать усвоению материала, а не просто выдавать готовые ответы.
"""

SUMMARY_PROMPT = """\
Ты выполняешь суммаризацию диалога между студентом и ассистентом курса.
Проанализируй представленный обмен сообщениями и составь краткое резюме, которое:
- сохранит **суть вопросов** студента;
- зафиксирует **ключевые моменты ответов** ассистента (включая ссылки на разделы курса, примеры,
  важные пояснения);
- будет **лаконичным и информативным** (2–3 предложения или несколько bullet points);
- напиши резюме **на том же языке**, что и диалог.

Резюме будет использовано как контекст при последующих обращениях, чтобы ассистент мог
поддерживать непрерывность беседы и не терять важные детали.

Пример:
Диалог:
Студент: Что такое градиентный спуск?
Ассистент: Градиентный спуск — это метод оптимизации, который минимизирует функцию потерь.
В курсе он разбирается в модуле 3 «Оптимизация». Мы итеративно движемся против градиента.
Резюме: Студент спрашивал о градиентном спуске.
Ассистент объяснил суть метода и указал на модуль 3.
"""

summarization_middleware = SummarizationMiddleware(
    model=model,
    trigger=("tokens", 8000),
    keep=("messages", 25),
    summary_prompt=SUMMARY_PROMPT,
)


async def call_chatbot(course_id: UUID, user_id: int, user_prompt: str) -> str:
    """Вызов агента для ответов на вопросы студентов"""

    async with AsyncSqliteSaver.from_conn_string(str(SQLITE_PATH)) as checkpointer:
        await checkpointer.setup()
        agent = create_agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            middleware=[summarization_middleware],
            tools=[knowledge_search],
            checkpointer=checkpointer,
        )
        result = await agent.ainvoke(
            {"messages": [("human", user_prompt)]},
            context=CourseContext(course_id=course_id),
            config={"configurable": {"thread_id": f"{user_id}"}}
        )
    return result["messages"][-1].content
