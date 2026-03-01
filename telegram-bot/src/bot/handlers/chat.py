from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.infra.ai.agents.chatbot.agent import call_chatbot
from src.infra.db.conn import session_factory
from src.infra.db.repos import StudentRepository
from src.utils.formatting import sanitize_for_telegram

from ..fsm import ChattingForm
from ..lexicon import STUDENT_CMD_MENU_TEXT

router = Router(name=__name__)


def get_leave_chat_kb() -> InlineKeyboardMarkup:
    """Клавиатура для выхода из чата"""

    builder = InlineKeyboardBuilder()
    builder.button(text="🔚 Завершить диалог", callback_data="leave_chat")
    return builder.as_markup()


@router.message(Command("chat"))
async def cmd_chat(message: Message, state: FSMContext) -> None:
    """Начать чат с AI ассистентом"""

    async with session_factory() as session:
        repo = StudentRepository(session)
        group = await repo.get_student_group(message.from_user.id)
    await message.answer("Задайте свой вопрос ...")
    await state.update_data(course_id=group.course_id, group_id=group.id)
    await state.set_state(ChattingForm.in_message_typing)


@router.message(ChattingForm.in_message_typing, F.text)
async def process_message(message: Message, state: FSMContext) -> None:
    """Обработка сообщения студента"""

    data = await state.get_data()
    async with ChatActionSender.typing(chat_id=message.chat.id, bot=message.bot):
        content = await call_chatbot(
            course_id=data["course_id"], user_id=message.from_user.id, user_prompt=message.text
        )
        await message.reply(text=sanitize_for_telegram(content), reply_markup=get_leave_chat_kb())
        await state.set_state(ChattingForm.in_message_typing)


@router.callback_query(F.data == "leave_chat")
async def cb_leave_chat(query: CallbackQuery, state: FSMContext) -> None:
    """Выйти из чата с AI"""

    await query.answer()
    await state.clear()
    await query.message.answer(**STUDENT_CMD_MENU_TEXT.as_kwargs())
