import io
import logging

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...ai_agents.expert_interviewer.agent import Context, agent
from ...keyboards.inline import TeacherMenuAction, TeacherMenuCBData, get_teacher_menu_kb
from ...rag import get_rag_pipeline
from ...utils import convert_document_to_md

logger = logging.getLogger(__name__)

router = Router(name=__name__)

SUPPORTED_DOCUMENT_FORMATS = {"docx", "pdf", "pptx", "xlsx"}


class CourseForm(StatesGroup):
    """Форма для создания курса"""

    in_title_typing = State()
    waiting_for_document = State()
    in_interview = State()


class ConfirmCBData(CallbackData, prefix="creation_confirm"):
    confirm: str


def get_creation_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения процедуры создания курса"""

    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Продолжить", callback_data=ConfirmCBData(confirm="yes").pack())
    builder.button(text="❌ Отмена", callback_data=ConfirmCBData(confirm="no").pack())
    return builder.as_markup()


@router.callback_query(TeacherMenuCBData.filter(F.action == TeacherMenuAction.CREATE_COURSE))
async def cb_create_course(query: CallbackQuery) -> None:
    await query.answer()
    await query.message.answer(
        text="""🤖 Я помогу вам создать качественный образовательный курс.
        1. Укажите название курса
        2. Можете прикрепить образовательные материалы
        3. После чего я задам вам вопросы для уточнения деталей.
        """,
        reply_markup=get_creation_confirm_kb()
    )


@router.callback_query(ConfirmCBData.filter(F.confirm == "no"))
async def cb_cancel_course_creation(query: CallbackQuery) -> None:
    await query.answer()
    await query.message.edit_text(text="", reply_markup=get_teacher_menu_kb())


@router.callback_query(ConfirmCBData.filter(F.confirm == "yes"))
async def cb_confirm_course_creation(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await query.message.edit_text("Как будет называться ваш курс? (Введите название)")
    await state.set_state(CourseForm.in_title_typing)


def get_documents_done_kb(btn_text: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_text, callback_data="documents_done")
    return builder.as_markup()


@router.message(CourseForm.in_title_typing, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await message.answer(
        "Отлично! Теперь можете прикрепить материалы (DOCX, PDF, PPTX, ...)\n"
        "Можно отправить сразу несколько файлов одним сообщением.\n\n"
        "Когда закончите — нажмите кнопку ниже ↓",
        reply_markup=get_documents_done_kb("⏩ Пропустить"),
    )
    await state.set_state(CourseForm.waiting_for_document)


@router.message(CourseForm.waiting_for_document, F.document)
async def process_uploaded_document(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    documents = data.get("documents", [])
    if message.document.file_name.split(".")[-1] not in SUPPORTED_DOCUMENT_FORMATS:
        await message.answer(
            text=f"""⚠️ Неподдерживаемый документ: {message.document.file_name}
                Всего собрано файлов: {len(documents)}
                Можете отправить ещё или нажать кнопку «Готово»""",
            reply_markup=get_documents_done_kb("✅ Всё, готово → следующий шаг"),
        )
        return
    documents.append(message.document.file_id)
    await state.update_data(documents=documents)
    await message.answer(
        text=f"""✅ Получен документ: {message.document.file_name}
        Всего собрано файлов: {len(documents)}
        Можете отправить ещё или нажать кнопку «Готово»""",
        reply_markup=get_documents_done_kb("✅ Всё, готово → следующий шаг"),
    )


@router.callback_query(F.data == "documents_done")
async def cb_document_done(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    documents = data.get("documents", [])
    if not documents:
        ...
    rag_pipeline = get_rag_pipeline(index_name=f"materials-{query.from_user.id}-index")
    for file_id in documents:
        file_info = await query.bot.get_file(file_id)
        buffer = await query.bot.download_file(file_info.file_path, destination=io.BytesIO())
        file = buffer.getbuffer().tobytes()
        md_content = convert_document_to_md(
            file, file_extension=f".{file_info.file_path.split('.')[-1]}"
        )
        rag_pipeline.indexing(md_content, metadata={"source": file_info.file_path})
    await query.answer("Все материалы загружены")
    prompt = "Давай начнём интервью, проанализируй мои материалы и продумай вопросы"
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        config={"configurable": {"thread_id": f"{query.from_user.id}"}},
        context=Context(user_id=query.from_user.id, course_title=data["title"]),
    )
    await query.answer(result["messages"][-1].content)
    await state.set_state(CourseForm.in_interview)


@router.message(CourseForm.in_interview, F.text)
async def process_interview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    prompt = "Давай начнём интервью, проанализируй мои материалы и продумай вопросы"
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        config={"configurable": {"thread_id": f"{message.from_user.id}"}},
        context=Context(user_id=message.from_user.id, course_title=data["title"]),
    )
    if result.get("interview_result") is not None:
        return
    await message.answer(result["messages"][-1].content)
