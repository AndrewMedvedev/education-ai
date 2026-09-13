import logging
from uuid import UUID

from src.llm_service import Runtime, tool

from ..infra.database.repos.document import SqlDocumentRepository
from .course_generator.workflow import generate_course
from .schemas import Context, RuntimeContext

logger = logging.getLogger(__name__)


class State(RuntimeContext):
    chat_id: UUID
    task_id: str | None = None


@tool(
    name="get_table_of_contents",
    description="Достает все оглавления загруженных документов пользователя по id пользователя",
)
async def get_table_of_contents(runtime: Runtime[Context, State]) -> str | list[dict]:
    """Получает table of contents, чтобы вызывающий код работал через единый интерфейс."""
    answer = await SqlDocumentRepository(session=runtime.state.db_session).get_tocs(  # pyright: ignore[reportOptionalSubscript, reportOptionalMemberAccess, reportArgumentType]
        owner_id=runtime.context.user_id
    )
    if not answer:
        return "У пользователя нету документов"
    return [{"toc_id": model.id, "toc": model.title} for model in answer]  # type: ignore  # ruff:ignore[blanket-type-ignore]


@tool(
    name="get_titles",
    description="Достает все заголовки документа по id оглавления",
)
async def get_titles(
    runtime: Runtime[Context, State],
    toc_id: UUID,
) -> str | list[dict]:
    """Получает titles, чтобы вызывающий код работал через единый интерфейс."""
    answer = await SqlDocumentRepository(session=runtime.state.db_session).get_headings(  # pyright: ignore[reportOptionalSubscript, reportGeneralTypeIssues, reportArgumentType, reportOptionalMemberAccess]
        owner_id=runtime.context.user_id,
        toc_id=toc_id,
    )
    if not answer:
        return "У пользователя нету документов"
    return [{"heading_id": model.id, "title": model.title} for model in answer]


@tool(
    name="get_content",
    description="Достает текст документа по id заголовка",
)
async def get_content(runtime: Runtime[Context, State], heading_id: UUID) -> str:
    """Получает content, чтобы вызывающий код работал через единый интерфейс."""
    answer = await SqlDocumentRepository(session=runtime.state.db_session).get_text(  # pyright: ignore[reportArgumentType, reportOptionalMemberAccess]
        owner_id=runtime.context.user_id,
        heading_id=heading_id,
    )
    if answer is None or answer.content is None:
        return "У пользователя нету документов"
    return answer.content


@tool(
    name="complete_interview",
    description=(
        "Завершает интервью с пользователем, когда собраны все необходимые "
        "данные для генерации курса, и отправляет задачу на выполнение. "
        "Вызывается ровно один раз, когда интервью полностью завершено."
        "Промпт строго на Русском языке."
    ),
)
async def complete_interview(  # ruff: ignore[unused-async]
    prompt: str,
    runtime: Runtime[Context, State],
) -> str:
    """Выполняет действие `complete_interview`, чтобы поддержать основной сценарий модуля."""
    generation_context = Context(
        user_id=runtime.context.user_id,
        course_id=runtime.context.course_id,
        prompt=prompt,
    )

    result = generate_course.send(generation_context=generation_context.model_dump(mode="json"))
    runtime.state.task_id = result.message_id  # pyright: ignore[reportOptionalMemberAccess]
    return f"Курс поставлен в очередь на генерацию, task_id={result.message_id}, ,больше не вызывай никакие инструменты, заверши чат."  # ruff: ignore[line-too-long]
