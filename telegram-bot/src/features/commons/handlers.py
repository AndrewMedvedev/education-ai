from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from src.core.database import session_factory
from src.features.user import repository, service
from src.features.user.schemas import UserRole

from .keyboards import RoleSelectionCbData, get_role_selection_kb
from .lexicon import WELCOME_STUDENT_TEXT, WELCOME_TEACHER_TEXT

router = Router(name=__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with session_factory() as session:
        user = await repository.get(session, message.from_user.id)
    if user is None:
        await message.reply(
            text="**Добро пожаловать!** Для начала выберите кем вы являетесь",
            reply_markup=get_role_selection_kb()
        )
        return
    if user.role == UserRole.TEACHER:
        from src.features.teacher.keyboards import get_menu_kb

        await message.reply(**WELCOME_TEACHER_TEXT.as_kwargs(), reply_markup=get_menu_kb())
        return
    if user.role == UserRole.STUDENT:
        from src.features.student.keyboards import get_menu_kb

        await message.reply(**WELCOME_STUDENT_TEXT.as_kwargs(), reply_markup=get_menu_kb())
        return


@router.callback_query(RoleSelectionCbData.filter(F.role == UserRole.TEACHER))
async def cb_select_teacher_role(query: CallbackQuery, callback_data: RoleSelectionCbData) -> None:
    from src.features.teacher.keyboards import get_menu_kb

    await query.answer()
    await service.create_from_message(query, callback_data.role)
    await query.message.answer(**WELCOME_TEACHER_TEXT.as_kwargs(), reply_markup=get_menu_kb())


@router.callback_query(RoleSelectionCbData.filter(F.role == UserRole.TEACHER))
async def cb_select_student_role(query: CallbackQuery, callback_data: RoleSelectionCbData) -> None:
    from src.features.student.keyboards import get_menu_kb

    await query.answer()
    await service.create_from_message(query, callback_data.role)
    await query.message.answer(**WELCOME_STUDENT_TEXT.as_kwargs(), reply_markup=get_menu_kb())
