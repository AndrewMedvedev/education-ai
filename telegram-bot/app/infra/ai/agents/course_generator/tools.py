from langchain.tools import ToolRuntime, tool

from ... import rag
from ..tools import SearchInput
from .schemas import TeacherContext


@tool(
    "materials_search",
    description="Выполняет поиск информации в материалах преподавателя",
    args_schema=SearchInput
)
def rag_search(runtime: ToolRuntime[TeacherContext], search_query: str) -> str:
    docs = rag.retrieve(search_query, metadata_filter={"tenant_id": runtime.context.tenant_id})
    return "\n\n".join(docs)
