from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.settings import settings

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
)

SYSTEM_PROMPT = """\
"""


async def call_assignment_checker(): ...
