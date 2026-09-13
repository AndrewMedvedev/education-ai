from typing import Any

import logging

from dramatiq import actor
from langchain_core.runnables import RunnableConfig

from src.core.database import session_factory

from ..schemas import RuntimeContext
from .helper import invoke_or_resume
from .nodes import Context, agent

logger = logging.getLogger(__name__)


@actor(
    max_retries=6,  # сколько раз повторить при ошибке
    min_backoff=10000,  # мин. задержка перед повтором (мс)
    max_backoff=100000,  # макс. задержка (мс)
    store_results=True,
    time_limit=5 * 60 * 60 * 1000,
)
async def generate_course(generation_context: dict[str, Any]) -> dict[str, str]:
    """Генерирует курс, чтобы автоматически подготовить часть учебного контента."""
    context = Context(**generation_context)
    try:
        async with session_factory() as session:
            await invoke_or_resume(
                graph=agent,
                input_data={"generation_context": context},
                config=RunnableConfig(
                    configurable={
                        "thread_id": f"course:{context.course_id}",
                    }
                ),
                context=RuntimeContext(db_session=session),
            )
            return {"course_id": str(context.course_id)}
    except Exception:
        logger.exception(
            "Course generation failed: course_id=%s",
            context.course_id,
        )
        raise
