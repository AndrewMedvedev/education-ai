import io
import logging
import time
from enum import StrEnum

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.broker import broker
from src.rag import get_rag_pipeline
from src.utils import convert_document_to_md

from ..keyboards import MenuAction, MenuCBData, get_menu_kb
from .ai_agent.agents.interviewer import UserContext, interviewer_agent
from .broker import CourseCreationTask

logger = logging.getLogger(__name__)

router = Router(name=__name__)

SUPPORTED_DOCUMENT_FORMATS = {"docx", "pdf", "pptx", "xlsx"}


class CourseCreationForm(StatesGroup):
    """Форма для создания курса"""

    in_title_typing = State()  # Ввод названия курса
    waiting_for_document = State()  # Загрузка материалов
    in_interview = State()  # Интервью с AI - агентом


class ConfirmAction(StrEnum):
    CONTINUE = "continue"
    CANCEL = "cancel"


class ConfirmCbData(CallbackData, prefix="confirm_creation"):
    action: ConfirmAction


def get_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения процедуры создания курса"""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="▶️ Продолжить",
        callback_data=ConfirmCbData(action=ConfirmAction.CONTINUE).pack()
    )
    builder.button(
        text="❌ Отмена",
        callback_data=ConfirmCbData(action=ConfirmAction.CANCEL).pack()
    )
    return builder.as_markup()


@router.callback_query(MenuCBData.filter(F.action == MenuAction.CREATE_COURSE))
async def cb_create_course(query: CallbackQuery) -> None:
    await query.answer()
    await query.message.answer(
        text="""🤖 Я помогу вам создать качественный образовательный курс.
        1. Укажите название курса
        2. Можете прикрепить образовательные материалы
        3. После чего я задам вам вопросы для уточнения деталей.
        """,
        reply_markup=get_confirm_kb()
    )


@router.callback_query(ConfirmCbData.filter(F.action == ConfirmAction.CANCEL))
async def cb_cancel_course_creation(query: CallbackQuery) -> None:
    await query.answer()
    await query.message.edit_text(text="Привет", reply_markup=get_menu_kb())


@router.callback_query(ConfirmCbData.filter(F.action == ConfirmAction.CONTINUE))
async def cb_confirm_course_creation(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    logger.info(
        "User `%s` started filling out form, current state is title typing",
        query.from_user.username
    )
    await query.message.edit_text("Как будет называться ваш курс? (Введите название)")
    await state.set_state(CourseCreationForm.in_title_typing)


def get_complete_uploading_kb(btn_text: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_text, callback_data="complete_uploading")
    return builder.as_markup()


@router.message(CourseCreationForm.in_title_typing, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    logger.info(
        "User `%s` entered '%s' course title", message.from_user.username, message.text
    )
    await message.answer(
        text=f"""Отличное название {message.text}! Теперь можете прикрепить материалы
        (DOCX, PDF, PPTX),
        которые я буду использовать внутри курса.

        Можно отправить сразу несколько файлов одним сообщением.
        Если у вас нет материалов, можете пропустить этот шаг ↓""",
        reply_markup=get_complete_uploading_kb("⏩ Пропустить"),
    )
    await state.set_state(CourseCreationForm.waiting_for_document)


@router.message(CourseCreationForm.waiting_for_document, F.document)
async def process_uploaded_document(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    documents = data.get("documents", [])
    file_name = message.document.file_name
    document_format = file_name.split(".")[-1]
    if document_format not in SUPPORTED_DOCUMENT_FORMATS:
        logger.warning(
            "User `%s` attached unsupported document `%s`",
            message.from_user.username, file_name
        )
        await message.answer(
            text=f"""
            🔗 <b>Файл:</b> <code>{file_name}</code>
            🚫 <b>Неподдерживаемый формат</b>: <code>{document_format.upper()}</code>
            📋 <b>Доступные форматы:</b> {', '.join(SUPPORTED_DOCUMENT_FORMATS)}
            📁 <b>Текущее количество файлов:</b> {len(documents)}
            📤 Отправьте подходящий файл или нажмите <b>«✔️ Завершить»</b>""",
            reply_markup=get_complete_uploading_kb("✔️ Завершить"),
        )
        return
    documents.append({"file_name": file_name, "file_id": message.document.file_id})
    await state.update_data(documents=documents)
    logger.info("User `%s` uploaded document `%s`", message.from_user.username, file_name)
    await message.answer(
        text=f"""
        🔗 <b>Получен файл:</b> <code>{message.document.file_name}</code>
        📁 <b>Файлов отправлено:</b> {len(documents)}
        📤 Можете отправить ещё файлы или нажать <b>«✔️ Завершить»</b>""",
        reply_markup=get_complete_uploading_kb("✔️ Завершить"),
    )


async def start_interview(
        user_id: int, course_title: str, uploaded_documents: list[str] | None = None
) -> str:
    """Начинает интервью с AI - агентом.

    :param user_id: Идентификатор пользователя.
    :param course_title: Название курса.
    :param uploaded_documents: Названия загруженных документов пользователя.
    :returns: Сгенерированный первый вопрос.
    """

    uploaded_materials_string = (
        "; ".join(uploaded_documents)
        if uploaded_documents
        else "Преподаватель не загрузил материалы"
    )
    prompt_template = f"""\
    **Название курса:** {course_title}
    **Загруженные материалы:** {uploaded_materials_string}

    Проанализируй материалы (если они есть), продумай интервью, после чего задай первый вопрос,
    чтобы начать интервью
    """
    thread_id = f"interview-{user_id}"
    result = await interviewer_agent.ainvoke(
        {"messages": [("human", prompt_template)]},
        config={"configurable": {"thread_id": thread_id}},
        context=UserContext(user_id=user_id),
    )
    return result["messages"][-1].content


@router.callback_query(F.data == "complete_uploading")
async def cb_complete_uploading(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    data = await state.get_data()
    documents = data.get("documents", [])
    if documents:
        logger.info(
            "User `%s` uploaded %s documents, starting process it",
            query.from_user.username, len(documents)
        )
        await query.message.answer(
            text="⏳ Начинаю обработку материалов, это может занять некоторое время ..."
        )
        index_name = f"materials-{query.from_user.id}-index"
        rag_pipeline = get_rag_pipeline(index_name=index_name)
        message = await query.message.answer("🔄 Обработка материалов: <b>0%</b>")
        start_time = time.time()
        for i, document in enumerate(documents):
            logger.info("Start processing %s/%s document", i + 1, len(documents))
            file_info = await query.bot.get_file(document["file_id"])
            buffer = await query.bot.download_file(file_info.file_path, destination=io.BytesIO())
            file = buffer.getbuffer().tobytes()
            file_extension = f".{file_info.file_path.split('.')[-1]}"
            md_content = convert_document_to_md(file, file_extension=file_extension)
            rag_pipeline.indexing(md_content, metadata={"source": file_info.file_path})
            load_percent = round(i + 1 / len(documents), 2) * 100
            await message.edit_text(f"⏳ Обработано материалов: <b>{load_percent}%</b>")
        processing_time = time.time() - start_time
        logger.info(
            "All documents processed, processing time %s seconds", round(processing_time, 2)
        )
        await message.edit_text("⚙️ Все материалы обработаны!")
    await query.message.answer("🔎 Начинаю анализ материалов ...")
    async with ChatActionSender.typing(chat_id=query.from_user.id, bot=query.bot):
        logger.info("Starting interview session with user `%s`", query.from_user.username)
        first_question = await start_interview(
            user_id=query.from_user.id,
            course_title=data["title"],
            uploaded_documents=[document["file_name"] for document in documents],
        )
    logger.info(
        "User `%s` must answer the first question in interview: '%s'",
        query.from_user.username, first_question[:100]
    )
    await query.message.answer(first_question)
    await state.set_state(CourseCreationForm.in_interview)


@router.message(CourseCreationForm.in_interview, F.text)
async def process_interview(message: Message, state: FSMContext) -> None:
    async with ChatActionSender.typing(chat_id=message.chat.id, bot=message.bot):
        thread_id = f"interview-{message.from_user.id}"
        result = await interviewer_agent.ainvoke(
            {"messages": [("human", message.text)]},
            config={"configurable": {"thread_id": thread_id}},
            context=UserContext(user_id=message.from_user.id),
        )
    summary = result.get("summary")
    if summary is not None:
        await state.clear()
        await message.answer(
            text="🤖 Спасибо за уделённое время, передаю ваши ответы AI агенту ..."
        )
        task = CourseCreationTask(user_id=message.from_user.id, interview_with_teacher=summary)
        await broker.publish(task, channel="course:creation")
        return
    await message.answer(result["messages"][-1].content)
