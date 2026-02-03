from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from src.core.database import session_factory
from src.features.user import repository, service
from src.features.user.schemas import UserRole

from .keyboards import RoleSelectionCbData, get_role_selection_kb

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
        from src.features.teacher.keyboards import get_menu_kb  # noqa: PLC0415

        await message.reply(
            text="""
            Добро пожаловать в панель управления! Вы можете:

            • 🤖 Создать курс с помощью AI
            • 👥 Управлять списком студентов
            • 📈 Отслеживать прогресс студентов
            """,
            reply_markup=get_menu_kb()
        )
        return
    if user.role == UserRole.STUDENT:
        from src.features.student.keyboards import get_menu_kb  # noqa: PLC0415

        await message.reply(
            text="""
            Я — твой помощник в обучении. Здесь ты можешь:

            • 🔑 Зарегистрироваться на курс
            • 📊 Следить за своей успеваемостью
            • 💬 Общаться с AI преподавателем
            """,
            reply_markup=get_menu_kb()
        )
        return


@router.callback_query(RoleSelectionCbData.filter(F.role == UserRole.TEACHER))
async def cb_select_teacher_role(query: CallbackQuery, callback_data: RoleSelectionCbData) -> None:
    await query.answer()
    await service.create_from_message(query, callback_data.role)

    from src.features.teacher.keyboards import get_menu_kb  # noqa: PLC0415

    await query.message.answer(
        text="""
        Добро пожаловать в панель управления! Вы можете:

        • 🤖 Создать курс с помощью AI
        • 👥 Управлять списком студентов
        • 📈 Отслеживать прогресс студентов
        """,
        reply_markup=get_menu_kb(),
    )


@router.callback_query(RoleSelectionCbData.filter(F.role == UserRole.TEACHER))
async def cb_select_student_role(query: CallbackQuery, callback_data: RoleSelectionCbData) -> None:
    await query.answer()
    await service.create_from_message(query, callback_data.role)

    from src.features.student.keyboards import get_menu_kb  # noqa: PLC0415

    await query.message.answer(
        text="""
        Добро пожаловать в панель управления! Вы можете:

        • 🤖 Создать курс с помощью AI
        • 👥 Управлять списком студентов
        • 📈 Отслеживать прогресс студентов
        """,
        reply_markup=get_menu_kb(),
    )
