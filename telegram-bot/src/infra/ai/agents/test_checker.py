# Агент для проверки тестов с развёрнутыми ответами

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI

from src.app.schemas import TestResult
from src.core.entities.course import DetailedAnswerTest
from src.settings import settings
from src.utils.formatting import prepare_test_for_checking

# model = ChatOpenAI(
#     api_key=settings.yandexcloud.api_key,
#     model=settings.yandexcloud.qwen3_235b,
#     base_url=settings.yandexcloud.base_url,
#     temperature=0.2,
# )

model = ChatOpenAI(
    api_key=settings.deepseek.api_key,
    base_url=settings.deepseek.base_url,
    model=settings.deepseek.deepseek_chat,
    temperature=0.2,
)

SYSTEM_PROMPT = """\
Ты — эксперт по оцениванию развёрнутых ответов в учебных тестах.
Твоя задача — проверить ответы студента на тест и выставить баллы в соответствии
с предоставленными критериями.

### Входные данные:
Тебе будет передан тест, содержащий список вопросов. Каждый вопрос включает:
 - Текст вопроса
 - Максимальный балл за вопрос
 - Эталонный ответ или критерии оценки (например, ключевые элементы, которые должны быть в ответе)
 - Ответ студента

### Правила оценивания:
 - Оценивай каждый вопрос объективно, основываясь на эталонном ответе или критериях.
 - Если ответ полностью верен — ставь максимальный балл.
 - Если ответ частично верен — ставь частичный балл пропорционально полноте и точности.
 - Если ответ отсутствует или полностью неверен — ставь 0 баллов.
 - Баллы за каждый вопрос должны быть целыми неотрицательными числами, не превышающими максимум.
"""


async def call_test_checker(given_answers: list[str], test: DetailedAnswerTest) -> TestResult:
    """Вызов агента для проверки тестирования с развёрнутыми ответами"""

    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        response_format=ProviderStrategy(TestResult),
    )
    result = await agent.ainvoke(
        {"messages": [("human", prepare_test_for_checking(given_answers, test))]}
    )
    return result["structured_response"]
