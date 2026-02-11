from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.features.auth.service import ForbiddenError, authenticate_student

from ..keyboards import MenuAction, MenuCBData, get_course_menu_kb, get_main_menu_kb
from ..lexicon import get_course_menu_text
from ..service import get_group_course
from .fsm import SignupForm
from .keyboards import SignupConfirmCbData, get_signup_confirm_kb

router = Router(name=__name__)


@router.callback_query(MenuCBData.filter(F.action == MenuAction.SIGNUP_FOR_COURSE))
async def cb_signup_for_course(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await query.message.answer(
        text=(
            "Для получение доступа к курсу, вам необходимо ввести учетные данные,"
            "которые вам выдал преподаватель"
        )
    )
    await query.message.answer("Введите логин:")
    await state.set_state(SignupForm.in_login_typing)


@router.message(SignupForm.in_login_typing, F.text)
async def process_login(message: Message, state: FSMContext) -> None:
    await state.update_data(login=message.text.strip())
    await message.answer("Введите пароль:")
    await state.set_state(SignupForm.in_password_typing)


@router.message(SignupForm.in_password_typing, F.text)
async def process_password(message: Message, state: FSMContext) -> None:
    await state.update_data(password=message.text.strip())
    await message.answer("Подтвердите вход", reply_markup=get_signup_confirm_kb())


@router.callback_query(SignupConfirmCbData.filter(F.action == "cancel"))
async def cb_cancel(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.clear()
    await query.message.answer("⚙️ Главное меню", reply_markup=get_main_menu_kb())


@router.callback_query(SignupConfirmCbData.filter(F.action == "enter"))
async def cb_enter(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    data = await state.get_data()
    login, password = data["login"], data["password"]
    try:
        student = await authenticate_student(
            user_id=query.from_user.id,
            login=login,
            password=password
        )
        await query.answer("✅ Вход успешно выполнен!")
    except ForbiddenError:
        await query.answer("🚫 Неверные учётные данные!", show_alert=True)
        await state.clear()
        return
    course = await get_group_course(student.group_id)
    content = get_course_menu_text(course.title)
    await query.message.answer(
        **content.as_kwargs(), reply_markup=get_course_menu_kb(student.group_id)
    )
