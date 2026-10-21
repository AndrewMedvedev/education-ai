import logging
from uuid import UUID

from langchain_core.runnables import RunnableConfig

from src.core.tkq import taskiq_broker
from src.courses.agents.course_generator.helper import invoke_or_resume
from src.courses.agents.schemas import Context, GenerationContext
from src.courses.dependencies.agents import CourseAgentDep, LessonAgentDep, ModuleAgentDep
from src.courses.dependencies.base import LessonRepoDep, VectorRepoDep
from src.courses.utils.formatting import get_lesson_context

logger = logging.getLogger(__name__)

RETRY_OPTS = {"retry_on_error": True, "max_retries": 5, "delay": 10, "timeout": 5 * 60 * 60}


@taskiq_broker.task(task_name="courses.generate_course", **RETRY_OPTS)
async def generate_course(context: Context, agent: CourseAgentDep) -> dict[str, UUID]:
    try:
        await invoke_or_resume(
            graph=agent,
            input_data={"generation_context": context},
            config=RunnableConfig(
                configurable={
                    "thread_id": f"course:{context.course_id}",
                }
            ),
        )
    except Exception:
        logger.exception(
            "Course generation failed: course_id=%s",
            context.course_id,
        )
        raise
    return {"course_id": context.course_id}


@taskiq_broker.task(task_name="courses.generate_module", **RETRY_OPTS)
async def generate_module(
    context: GenerationContext,
    audience_description: str,
    learning_objectives: list[str],
    description: str,
    agent: ModuleAgentDep,
) -> dict[str, UUID | int]:
    try:
        await invoke_or_resume(
            graph=agent,
            input_data={
                "generation_context": context,
                "audience_description": audience_description,
                "learning_objectives": learning_objectives,
                "order": context.order,
                "module_description": description,
            },
            config=RunnableConfig(
                configurable={
                    "thread_id": f"course:{context.course_id}:module:{context.order}",
                }
            ),
        )
    except Exception:
        logger.exception(
            "Module generation failed: course_id=%s order=%s",
            context.course_id,
            context.order,
        )
        raise
    return {"course_id": context.course_id, "module_order": context.order}


@taskiq_broker.task(task_name="courses.generate_lesson", **RETRY_OPTS)
async def generate_lesson(
    context: GenerationContext,
    audience_description: str,
    learning_objectives: list[str],
    description: str,
    agent: LessonAgentDep,
) -> dict[str, UUID | int]:
    try:
        await invoke_or_resume(
            graph=agent,
            input_data={
                "generation_context": context,
                "module_id": context.module_id,
                "audience_description": audience_description,
                "learning_objectives": learning_objectives,
                "order": context.order,
                "lesson_description": description,
            },
            config=RunnableConfig(
                configurable={
                    "thread_id": f"course:{context.course_id}:module:{context.module_id}:lesson:{context.order}",  # noqa: E501
                }
            ),
        )
    except Exception:
        logger.exception(
            "Lesson generation failed: course_id=%s module_id=%s order=%s",
            context.course_id,
            context.module_id,
            context.order,
        )
        raise
    return {
        "course_id": context.course_id,
        "module_id": context.module_id,  # pyright: ignore[reportReturnType]
        "lesson_order": context.order,
    }


@taskiq_broker.task(
    task_name="courses.index_lesson",
    retry_on_error=True,
    max_retries=2,
    delay=5,
    timeout=60,
)
async def index_lesson(
    course_id: UUID,
    lesson_id: UUID,
    lesson_repo: LessonRepoDep,
    vector_repo: VectorRepoDep,
) -> None:
    logger.info(
        "Starting lesson indexing: course_id=%s lesson_id=%s",
        course_id,
        lesson_id,
    )
    lesson = await lesson_repo.read(lesson_id)
    if lesson is None:
        logger.warning("Cannot index lesson %s: lesson not found", lesson_id)
        return
    try:
        lesson_text = get_lesson_context(lesson)
        document_id = f"lesson:{course_id}:{lesson.id}"

        await vector_repo.create(
            text=lesson_text,
            document_id=document_id,
            metadata={
                "course_id": str(course_id),
                "lesson_id": str(lesson.id),
                "document_id": document_id,
                "source": lesson.title,
                "category": "theory",
                "document_type": "lesson",
                "lesson_order": lesson.order,
            },
        )

        logger.info(
            "Indexed lesson %s for course %s as document %s",
            lesson.id,
            course_id,
            document_id,
        )
    except Exception:
        logger.exception(
            "Lesson indexing failed: course_id=%s lesson_id=%s",
            course_id,
            lesson_id,
        )
        raise
