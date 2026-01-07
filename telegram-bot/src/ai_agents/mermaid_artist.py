from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..settings import PROMPTS_DIR, settings

SYSTEM_PROMPT = (PROMPTS_DIR / "mermaid_artist.md").read_text(encoding="utf-8")

llm = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.aliceai_llm,
    base_url=settings.yandexcloud.base_url,
    temperature=0,
    max_retries=3
)

agent = (
        ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT)])
        | llm
        | StrOutputParser()
)
