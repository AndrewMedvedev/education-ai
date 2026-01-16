from typing import Annotated, Any

import logging
import operator

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, dynamic_prompt
from langchain.tools import ToolRuntime, tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, Field, PositiveInt

from ...services.rag import RAGPipeline
from ...settings import settings
from ...storage import telegram as telegram_storage
from ...utils import convert_document_to_markdown

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.aliceai_llm,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
    max_retries=3
)

rag_pipeline = RAGPipeline(embeddings=..., index_prefix="interview")


class Context(BaseModel):
    user_id: PositiveInt


class State(AgentState):
    interview: Annotated[list[tuple[str, str]], operator.add]
    file_ids: Annotated[list[str], operator.add]
    materials_summaries: Annotated[list[tuple[str, str]], operator.add]
    is_finished: bool


async def summarize_material(text: str, file_id: str, filename: str) -> str:
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
    return f"""Краткое содержание для {filename} (File-ID: {file_id}):
    {summary}
    """


class MaterialLoaderMiddleware(AgentMiddleware):
    @staticmethod
    async def _load_material(user_id: int, file_id: str) -> str:
        file = await telegram_storage.download_file(file_id)
        md_text = convert_document_to_markdown(file_data=file.data, file_extension=file.extension)
        rag_pipeline.indexing(
            index_name=f"materials-{user_id}",
            text=md_text,
            metadata={"filename": file.path},
        )
        return await summarize_material(md_text, file_id, file.path)

    async def abefore_model(
            self, state: State, runtime: Runtime[Context]
    ) -> dict[str, Any] | None:
        materials_summaries: list[tuple[str, str]] = []
        for file_id, _ in state.get("materials_summaries", []):
            if file_id not in state.get("file_ids", []):
                summary = await self._load_material(runtime.context.user_id, file_id)
                materials_summaries.append((file_id, summary))
        return {"materials_summaries": materials_summaries}


@dynamic_prompt
def state_aware_system_prompt(request: ModelRequest) -> str: ...


class MaterialsSearchInput(BaseModel):
    """Входные параметры для поиска по прикреплённым материалам"""

    search_query: str = Field(description="Запрос для поиска")
    filename: str | None = Field(description="Имя файла для поиска в нём информации")


@tool(
    "search_in_materials",
    description="Выполняет поиск по материалам эксперта",
    args_schema=MaterialsSearchInput,
)
def materials_search(
        runtime: ToolRuntime[Context, State], search_query: str, filename: str | None = None
) -> str:
    metadata_filtering: dict[str, str] | None = None
    if filename is not None:
        metadata_filtering = {"filename": filename}
    documents = rag_pipeline.retrieve(
        index_name=f"materials-{runtime.context.user_id}",
        query=search_query,
        metadata_filtering=metadata_filtering,
    )
    return "\n\n".join(documents)


class SaveQAInput(BaseModel):
    """Входные параметры для сохранения пары вопрос-ответ"""

    question: str = Field(description="Вопрос который был задан эксперту")
    answer: str = Field(description="Ответ эксперта на вопрос")


@tool(
    "save_question_answer_pair",
    description="Сохраняет пару вопрос ответ в интервью",
    args_schema=SaveQAInput,
)
def save_qa(question: str, answer: str) -> Command:
    return Command(update={"interview": [(question, answer)]})


agent = create_agent(
    model=model,
    tools=[materials_search, save_qa],
    middleware=[MaterialLoaderMiddleware(), state_aware_system_prompt],
)
