import asyncio

from faststream import Logger
from faststream.redis import RedisRouter

from ..keyboards import get_modules_kb
from .ai_agent.workflow import agent
from .commands import CourseCreationCommand

router = RedisRouter()


@router.subscriber("course:creation")
async def handle_course_creation(command: CourseCreationCommand, logger: Logger) -> None:
    from tg_bot.core.bot import bot

    await bot.send_message("🤖 Начинаю создание курса, это займёт некоторое время ...")
    result = await agent.ainvoke({
        "user_id": command.user_id, "interview_with_teacher": command.interview_with_teacher
    })
    course = result.get("course")
    if course is None:
        logger.error("Course creation failed, course is not created!")
        await bot.send_message(
            chat_id=command.user_id,
            text="⚠️ Сожалеем, произошла ошибка при генерации курса ..."
        )
        return
    await bot.send_message(
        chat_id=command.user_id,
        text="🎉 Курс сгенерирован! Не забудьте проверить материал перед публикацией"
    )
    await asyncio.sleep(1)
    await bot.send_message(
        chat_id=command.user_id,
        text=(
            f"<b>{course.title}</b>\n\n"
            f"<i>{course.description}</i>"
        ),
        reply_markup=get_modules_kb(course.modules)
    )
