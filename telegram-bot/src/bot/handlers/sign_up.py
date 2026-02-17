from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.entities.user import AnyUser, Student, UserRole
from src.infra.db.conn import session_factory
from src.infra.db.repos import UserRepository

from ..fsm import StudentSignUpForm
from ..keyboards import UserChoiceCbData

router = Router(name=__name__)


@router.callback_query(UserChoiceCbData.filter(F.role == UserRole.STUDENT))
async def cb_student_chosen(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await query.message.answer(..., reply_markup=...)
    await state.set_state(StudentSignUpForm.in_group_selecting)
