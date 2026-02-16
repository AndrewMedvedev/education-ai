import io

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from tg_bot.core.database import session_factory
from tg_bot.features.auth.utils import get_student_list_template
from tg_bot.features.course import repository
from tg_bot.features.student import repository as student_repo
from tg_bot.features.student.schemas import Group

from ..keyboards import CourseMenuAction, CourseMenuCbData, get_course_menu_kb
from ..lexicon import get_course_preview_text
from .fsm import GroupCreationForm
from .keyboards import (
    ConfirmCbData,
    GroupsMenuAction,
    GroupsMenuCbData,
    get_confirm_kb,
    get_groups_menu_kb,
)
from .lexicon import GROUP_CREATION_INTRO_TEXT
from .service import add_students_in_group

router = Router(name=__name__)


@router.callback_query(CourseMenuCbData.filter(F.action == CourseMenuAction.GET_GROUPS))
async def cb_get_groups(query: CallbackQuery, callback_data: CourseMenuCbData) -> None:
    await query.answer()
    await query.message.edit_text(
        text="☰ Управление группами", reply_markup=get_groups_menu_kb(callback_data.course_id)
    )


@router.callback_query(GroupsMenuCbData.filter(F.action == GroupsMenuAction.BACK))
async def cb_back_action(query: CallbackQuery, callback_data: GroupsMenuCbData) -> None:
    await query.answer()
    async with session_factory() as session:
        course = await repository.get(session, callback_data.course_id)
    content = get_course_preview_text(
        title=course.title,
        description=course.description,
        learning_objectives=course.learning_objectives,
    )
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_course_menu_kb(course.id)
    )


@router.callback_query(GroupsMenuCbData.filter(F.action == GroupsMenuAction.ADD_GROUP))
async def cb_add_group_action(query: CallbackQuery, callback_data: GroupsMenuCbData) -> None:
    await query.answer()
    await query.message.edit_text(
        **GROUP_CREATION_INTRO_TEXT.as_kwargs(),
        reply_markup=get_confirm_kb(callback_data.course_id)
    )


@router.callback_query(ConfirmCbData.filter(F.action == "cancel"))
async def cb_cancel_action(query: CallbackQuery, callback_data: ConfirmCbData) -> None:
    await query.answer()
    await query.message.edit_text(
        text="☰ Управление группами", reply_markup=get_groups_menu_kb(callback_data.course_id)
    )


@router.callback_query(ConfirmCbData.filter(F.action == "continue"))
async def cb_continue_action(
        query: CallbackQuery, callback_data: ConfirmCbData, state: FSMContext
) -> None:
    await query.answer()
    await query.message.answer("Введите название группы:")
    await state.set_state(GroupCreationForm.in_title_typing)
    await state.update_data(course_id=callback_data.course_id)


@router.message(GroupCreationForm.in_title_typing, F.text)
async def process_group_title(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    group = Group(
        course_id=data["course_id"],
        teacher_id=message.from_user.id,
        title=message.text.strip(),
    )
    await state.update_data(group=group)
    async with session_factory() as session:
        course = await repository.get(session, data["course_id"])
    await message.reply(
        "Теперь заполните шаблон списка группы согласно инструкции и отправьте его мне "
    )
    excel_file = get_student_list_template(
        course_title=course.title,
        group_title=message.text.strip(),
        include_instruction=True,
    )
    await message.bot.send_document(message.chat.id, document=BufferedInputFile(
        file=excel_file,
        filename=f"{course.title}_{message.text.strip()}_Шаблон.xlsx",
    ))
    await state.update_data(course_title=course.title)
    await state.set_state(GroupCreationForm.waiting_for_students_list)


@router.message(GroupCreationForm.waiting_for_students_list, F.document)
async def process_students_list(message: Message, state: FSMContext) -> None:
    if message.document.file_name.split(".")[-1] != "xlsx":
        await message.reply("Неподдерживаемый формат файла!")
        return
    data = await state.get_data()
    group = data["group"]
    async with session_factory() as session:
        await student_repo.add_group(session, group)
        await session.commit()
    file_info = await message.bot.get_file(message.document.file_id)
    buffer = await message.bot.download_file(file_info.file_path, destination=io.BytesIO())
    input_file = buffer.getbuffer().tobytes()
    output_file = await add_students_in_group(group.id, input_file)
    await message.bot.send_document(
        message.chat.id,
        document=BufferedInputFile(
            file=output_file,
            filename=f"{data['course_title']}_{group.title}_Доступы.xlsx",
        ),
    )
    await state.clear()
