from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import Bold, Text, Underline, as_line, as_marked_section

from src.core.entities.user import Student, UserRole
from src.infra.db.conn import session_factory
from src.infra.db.repos import StudentRepository, UserRepository

from ..fsm import StudentSignUpForm
from ..keyboards import (
    ConfirmSignUpCbData,
    GroupChoiceCbData,
    UserChoiceCbData,
    get_confirm_sign_up_kb,
    get_group_choice_kb,
)
from ..lexicon import CONFETTI_EFFECT_ID, STUDENT_CMD_MENU_TEXT

router = Router(name=__name__)


@router.callback_query(UserChoiceCbData.filter(F.role == UserRole.STUDENT))
async def cb_student_chosen(query: CallbackQuery, state: FSMContext) -> None:
    """Выбрана роль студента"""

    await query.answer()
    async with session_factory() as session:
        repo = StudentRepository(session)
        groups = await repo.get_groups()
    await query.message.edit_text(
        text="👥 Выберите свою группу:", reply_markup=get_group_choice_kb(groups)
    )
    await state.set_state(StudentSignUpForm.in_group_choice)


@router.callback_query(StudentSignUpForm.in_group_choice, GroupChoiceCbData.filter())
async def process_group_choice(
        query: CallbackQuery, callback_data: GroupChoiceCbData, state: FSMContext
) -> None:
    """Обработка выбранной группы"""

    await query.answer()
    await state.update_data(group_id=callback_data.group_id)
    await query.message.edit_text(text="✍️ Введите ФИО:")
    await state.set_state(StudentSignUpForm.waiting_for_full_name)


@router.message(StudentSignUpForm.waiting_for_full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    """Обработка ФИО студента + сверка введённых данных"""

    await state.update_data(full_name=message.text.strip())
    data = await state.get_data()
    group_id, full_name = data["group_id"], data["full_name"]
    async with session_factory() as session:
        repo = StudentRepository(session)
        groups = await repo.get_groups()
    group = next((group for group in groups if group.id == group_id), None)
    await message.answer(
        **Text(
            as_marked_section(
                "✏️ Сверьте свои данные перед регистрацией",
                as_line(Bold("Группа:"), Underline(group.title), sep=" "),
                as_line(Bold("ФИО:"), Underline(full_name), sep=" "),
            )
        ).as_kwargs(), reply_markup=get_confirm_sign_up_kb()
    )


@router.callback_query(ConfirmSignUpCbData.filter(F.action == "cancel"))
async def cb_cancel_sign_up(query: CallbackQuery, state: FSMContext) -> None:
    """Отмена регистрации. Перенаправление на команду /start"""

    from .start import cmd_start

    await state.clear()
    await cmd_start(query.message)


@router.callback_query(ConfirmSignUpCbData.filter(F.action == "ok"))
async def cb_confirm_sign_up(query: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение регистрации студента на курс"""

    await query.answer()
    async with session_factory() as session:
        data = await state.get_data()
        group_id, full_name = data["group_id"], data["full_name"]
        student = Student(
            id=query.from_user.id,
            username=query.from_user.username,
            group_id=group_id,
            full_name=full_name,
        )
        repo = UserRepository(session)
        await repo.create(student)
    await query.message.delete()
    await query.message.answer(
        text="🎉 Вы успешно зарегистрированы", message_effect_id=CONFETTI_EFFECT_ID
    )
    await query.message.answer(STUDENT_CMD_MENU_TEXT)
    await state.clear()
