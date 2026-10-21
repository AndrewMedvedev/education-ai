import logging
from uuid import UUID

from pydantic import BaseModel

from src.llm_service import Runtime, tool

from ..infra.database.repos.document import SqlDocumentRepository
from .schemas import Context, GenerationContext, RuntimeContext

logger = logging.getLogger(__name__)


class State(RuntimeContext):
    chat_id: UUID
    task_id: str | None = None


@tool(
    name="get_table_of_contents",
    description="Достает все оглавления загруженных документов пользователя по id пользователя",
)
async def get_table_of_contents(runtime: Runtime[Context, State]) -> str | list[dict]:
    answer = await SqlDocumentRepository(session=runtime.state.db_session).get_tocs(  # pyright: ignore[reportOptionalSubscript, reportOptionalMemberAccess, reportArgumentType]
        owner_id=runtime.context.user_id
    )
    if not answer:
        return "У пользователя нету документов"
    return [{"toc_id": str(model.id), "toc": model.title} for model in answer]


@tool(
    name="get_titles",
    description="Достает все заголовки документа по id оглавления",
)
async def get_titles(
    runtime: Runtime[Context, State],
    toc_id: UUID,
) -> str | list[dict]:
    answer = await SqlDocumentRepository(session=runtime.state.db_session).get_headings(  # pyright: ignore[reportOptionalSubscript, reportGeneralTypeIssues, reportArgumentType, reportOptionalMemberAccess]
        owner_id=runtime.context.user_id,
        toc_id=toc_id,
    )
    if not answer:
        return "У пользователя нету документов"
    return [{"heading_id": str(model.id), "title": model.title} for model in answer]


@tool(
    name="get_content",
    description="Достает текст документа по id заголовка",
)
async def get_content(runtime: Runtime[Context, State], heading_id: UUID) -> str:
    answer = await SqlDocumentRepository(session=runtime.state.db_session).get_text(  # pyright: ignore[reportOptionalMemberAccess]
        owner_id=runtime.context.user_id,
        heading_id=heading_id,
    )
    if answer is None or answer.content is None:
        return "У пользователя нету документов"
    return answer.content


@tool(
    name="send_course_for_generation",
    description=(
        "Отправляет курс на генерацию после завершения интервью. Вызывай инструмент "
        "ровно один раз, только когда собраны требования к теме, целевой аудитории, "
        "уровню сложности, целям обучения и содержанию курса. Передай в prompt "
        "полное и непротиворечивое техническое задание на русском языке. После "
        "успешного вызова не вызывай другие инструменты и заверши диалог."
    ),
)
async def send_course_for_generation(
    prompt: str,
    runtime: Runtime[Context, State],
) -> str:
    context = Context(
        user_id=runtime.context.user_id,
        course_id=runtime.context.course_id,
        prompt=prompt,
    )
    from src.courses.infra.tasks import generate_course  # noqa: PLC0415

    task = await generate_course.kiq(context=context)  # pyright: ignore[reportCallIssue]

    runtime.state.task_id = task.task_id  # pyright: ignore[reportOptionalMemberAccess]
    return f"Курс поставлен в очередь на генерацию, task_id={task.task_id}, ,больше не вызывай никакие инструменты, заверши чат."  # noqa: E501


class GenerationInput(BaseModel):
    audience_description: str
    learning_objectives: list[str]
    description: str


@tool(
    name="send_module_for_generation",
    description=(
        "Отправляет модуль курса на генерацию после завершения интервью. Вызывай "
        "инструмент ровно один раз, когда определены целевая аудитория, цели обучения "
        "и подробное описание модуля. "
        "Все текстовые поля заполняй на русском "
        "языке. После успешного вызова не вызывай другие инструменты и заверши диалог."
    ),
)
async def send_module_for_generation(
    structure: GenerationInput,
    runtime: Runtime[GenerationContext, State],
) -> str:
    from src.courses.infra.tasks import generate_module  # noqa: PLC0415

    task = await generate_module.kiq(  # pyright: ignore[reportCallIssue]
        context=runtime.context,
        audience_description=structure.audience_description,
        learning_objectives=structure.learning_objectives,
        description=structure.description,
    )

    runtime.state.task_id = task.task_id  # pyright: ignore[reportOptionalMemberAccess]
    return f"Модуль поставлен в очередь на генерацию, task_id={task.task_id}, ,больше не вызывай никакие инструменты, заверши чат."  # noqa: E501


@tool(
    name="send_lesson_for_generation",
    description=(
        "Отправляет урок на генерацию после завершения интервью. Вызывай инструмент "
        "ровно один раз, когда определены целевая аудитория, цели обучения и подробное "
        "описание урока. "
        "Все текстовые поля заполняй "
        "на русском языке. После успешного вызова не вызывай другие инструменты и "
        "заверши диалог."
    ),
)
async def send_lesson_for_generation(
    structure: GenerationInput,
    runtime: Runtime[GenerationContext, State],
) -> str:
    from src.courses.infra.tasks import generate_lesson  # noqa: PLC0415

    task = await generate_lesson.kiq(  # pyright: ignore[reportCallIssue]
        context=runtime.context,
        audience_description=structure.audience_description,
        learning_objectives=structure.learning_objectives,
        description=structure.description,
    )

    runtime.state.task_id = task.task_id  # pyright: ignore[reportOptionalMemberAccess]
    return f"Урок поставлен в очередь на генерацию, task_id={task.task_id},   больше не вызывай никакие инструменты, заверши чат."  # noqa: E501
