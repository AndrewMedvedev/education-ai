from typing import Annotated

import logging
import operator

from langchain.agents import AgentState
from langchain.tools import ToolRuntime
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, PositiveInt

from ...settings import settings
from ...storage import telegram as tg_store
from ...utils import convert_document_to_markdown
from .rag import ExpertMaterialsSessionRAG

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.aliceai_llm,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
    max_retries=3
)

rag = ExpertMaterialsSessionRAG(embeddings=...)


class Context(BaseModel):
    expert_id: PositiveInt


class State(AgentState):
    interview: Annotated[list[tuple[str, str]], operator.add]
    tg_file_ids: Annotated[list[str], operator.add]
    expert_materials_summaries: Annotated[list[str], operator.add]
    is_finished: bool


async def summarize_expert_material(text: str, tg_file_id: str, filename: str) -> str:
    llm = ChatOpenAI(
        api_key=settings.yandexcloud.apikey,
        model=settings.yandexcloud.qwen3_235b,
        base_url=settings.yandexcloud.base_url,
        temperature=0.2,
        max_retries=3
    )
    prompt = ChatPromptTemplate.from_template(...)
    chain = prompt | llm | StrOutputParser()
    summary = await chain.ainvoke({"text": text})
    return f"""Краткое содержание для {filename} (Telegram-File-ID: {tg_file_id}):
    {summary}
    """


async def load_expert_material(runtime: ToolRuntime[Context, State], tg_file_id: str) -> Command:
    file = await tg_store.download_file(tg_file_id)
    md_text = convert_document_to_markdown(
        file_data=file.data, file_extension=file.extension
    )
    rag.index_document(
        expert_id=runtime.context.expert_id,
        text=md_text,
        metadata={"filename": file.path},
    )
    summary = await summarize_expert_material(md_text, tg_file_id, file.path)
    return Command(update={"expert_materials_summaries": [summary]})
