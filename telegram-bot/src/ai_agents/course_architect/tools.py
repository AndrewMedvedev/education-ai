from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from ...rag import get_rag_pipeline
from .workflow import Context


class MaterialsSearchInput(BaseModel):
    """Входные параметры для поиска по прикреплённым материалам"""

    search_query: str = Field(description="Запрос для поиска")


@tool(
    "search_in_materials",
    description="Выполняет поиск по материалам эксперта",
    args_schema=MaterialsSearchInput,
)
def materials_search(runtime: ToolRuntime[Context], search_query: str) -> str:
    index_name = f"materials-{runtime.context.user_id}-index"
    rag_pipeline = get_rag_pipeline(index_name=index_name)
    documents = rag_pipeline.retrieve(search_query)
    return "\n\n".join(documents)
