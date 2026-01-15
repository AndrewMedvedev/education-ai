from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field, PositiveInt

from ...core.schemas import TeacherInputs
from ...rag.education_materials import retrieve_education_materials


class EduMaterialsSearchInput(BaseModel):
    search_query: str = Field(
        description="Запрос для поиска информации в образовательных материалах"
    )
    top_k: PositiveInt = Field(
        default=10, description="Количество извлекаемых документов"
    )


@tool(
    "search_in_education_materials",
    description="",
    args_schema=EduMaterialsSearchInput,
)
async def education_materials_search(
        runtime: ToolRuntime[TeacherInputs], search_query: str, top_k: int = 10
) -> str:
    results = await retrieve_education_materials(
        teacher_id=runtime.context.user_id, search_query=search_query, top_k=top_k
    )
    return "\n\n".join(results)
