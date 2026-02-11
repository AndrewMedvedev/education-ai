from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.core.database import session_factory

from ... import repository
from ...keyboards import CourseMenuAction, CourseMenuCbData
from ..lexicon import get_my_progress_text

router = Router(name=__name__)


@router.callback_query(CourseMenuCbData.filter(F.action == CourseMenuAction.MY_PROGRESS))
async def cb_my_progress(query: CallbackQuery, callback_data: CourseMenuCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        group = await repository.get_group(session, callback_data.group_id)
        student = await repository.find_student_in_group(
            session, group.id, user_id=query.from_user.id
        )
    content = get_my_progress_text(
        full_name=student.full_name,
        login=student.login,
        group_title=group.title,
        created_at=student.created_at
    )
    await query.message.answer(**content.as_kwargs())
