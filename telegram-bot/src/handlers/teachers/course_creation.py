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

    in_title_typing = State()  # Ввод названия курса
    waiting_for_document = State()  # Загрузка материалов
    in_interview = State()  # Интервью с AI - агентом


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


def get_finalize_uploading_kb(btn_text: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_text, callback_data="finalize_uploading")
    return builder.as_markup()


@router.message(CourseForm.in_title_typing, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await message.answer(
        text=f"""Отличное название {message.text}! Теперь можете прикрепить материалы
        (DOCX, PDF, PPTX),
        которые я буду использовать внутри курса.

        Можно отправить сразу несколько файлов одним сообщением.
        Если у вас нет материалов, можете пропустить этот шаг ↓""",
        reply_markup=get_finalize_uploading_kb("⏩ Пропустить"),
    )
    await state.set_state(CourseForm.waiting_for_document)


@router.message(CourseForm.waiting_for_document, F.document)
async def process_uploaded_document(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    documents = data.get("documents", [])
    file_name = message.document.file_name
    document_format = file_name.split(".")[-1]
    if document_format not in SUPPORTED_DOCUMENT_FORMATS:
        await message.answer(
            text=f"""🔗 <b>Файл:</b> <code>{file_name}</code>

            🚫 <b>Неподдерживаемый формат</b>: <code>{document_format.upper()}</code>

            📋 <b>Доступные форматы:</b> {', '.join(SUPPORTED_DOCUMENT_FORMATS)}

            📁 <b>Текущее количество файлов:</b> {len(documents)}

            📤 Отправьте подходящий файл или нажмите <b>«✅ Готово»</b>""",
            reply_markup=get_finalize_uploading_kb("✅ Готово"),
        )
        return
    documents.append(message.document.file_id)
    await state.update_data(documents=documents)
    await message.answer(
        text=f"""🔗 <b>Получен файл:</b> <code>{message.document.file_name}</code>

        📁 <b>Всего файлов:</b> {len(documents)}

        📤 Можете отправить ещё файлы или нажать <b>«✅ Готово»</b>""",
        reply_markup=get_finalize_uploading_kb("✅ Готово"),
    )


async def start_interview(user_id: int, course_title: str) -> str:
    """Начинает интервью с AI - агентом.

    :param user_id: Идентификатор пользователя.
    :param course_title: Название курса.
    :returns: Сгенерированный первый вопрос.
    """

    prompt = "Проанализируй материалы, продумай интервью после чего задай первый вопрос"
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        config={"configurable": {"thread_id": f"{user_id}"}},
        context=Context(user_id=user_id, course_title=course_title),
    )
    return result["messages"][-1].content


@router.callback_query(F.data == "finalize_uploading")
async def cb_finalize_uploading(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    data = await state.get_data()
    documents = data.get("documents", [])
    if not documents:
        ...
    await query.message.answer(
        text="⏳ Начинаю обработку материалов, это может занять некоторое время ..."
    )
    rag_pipeline = get_rag_pipeline(index_name=f"materials-{query.from_user.id}-index")
    message = await query.message.answer("🔄 Обработка материалов: <b>0%</b>")
    for i, file_id in enumerate(documents):
        file_info = await query.bot.get_file(file_id)
        buffer = await query.bot.download_file(file_info.file_path, destination=io.BytesIO())
        file = buffer.getbuffer().tobytes()
        md_content = convert_document_to_md(
            file, file_extension=f".{file_info.file_path.split('.')[-1]}"
        )
        rag_pipeline.indexing(md_content, metadata={"source": file_info.file_path})
        load_percent = round(i + 1 / len(documents), 2) * 100
        await message.edit_text(f"🔄 Обработка материалов: <b>{load_percent}%</b>")
    await message.edit_text("⚙️ Все материалы обработаны!")
    first_question = await start_interview(
        user_id=query.from_user.id, course_title=data["title"]
    )
    await query.message.answer(first_question)
    await state.set_state(CourseForm.in_interview)


@router.message(CourseForm.in_interview, F.text)
async def process_interview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    result = await agent.ainvoke(
        {"messages": [("human", message.text)]},
        config={"configurable": {"thread_id": f"{message.from_user.id}"}},
        context=Context(user_id=message.from_user.id, course_title=data["title"]),
    )
    if result.get("interview_result") is not None:
        return
    await message.answer(result["messages"][-1].content)
