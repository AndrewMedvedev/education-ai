from faststream.redis import RedisRouter
from pydantic import BaseModel, PositiveInt

from .ai_agent.workflow import agent

router = RedisRouter()


class CourseCreationTask(BaseModel):
    """Задача на создание курса с помощью AI агента"""

    user_id: PositiveInt
    interview_with_teacher: str


@router.subscriber("course:creation")
async def handle_course_creation_task(task: CourseCreationTask):
    from src.core.bot import bot  # noqa: PLC0415

    await agent.ainvoke({
        "user_id": task.user_id, "interview_with_teacher": task.interview_with_teacher
    })
    await bot.send_message(chat_id=task.user_id, text="Курс создан")
