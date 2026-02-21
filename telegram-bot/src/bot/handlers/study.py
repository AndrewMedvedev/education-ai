import asyncio
import random

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import (
    BlockQuote,
    Bold,
    Text,
    Underline,
    as_line,
    as_numbered_section,
)

from src.app.services import check_multiple_choice_test, save_test_result
from src.core.commons import current_datetime
from src.core.entities.course import Module, TestType
from src.core.entities.student import LearningProgress
from src.infra.ai.agents.knowledge_tester import call_knowledge_tester
from src.infra.db.conn import session_factory
from src.infra.db.repos import CourseRepository, StudentRepository

from ..fsm import TestPassingForm
from ..keyboards import (
    ModuleAction,
    ModuleCbData,
    ModuleStudyCbData,
    OptionChoiceCbData,
    StartTestCbData,
    get_module_study_kb,
    get_modules_kb,
    get_options_choice_kb,
    get_start_test_kb,
)
from ..setup import storage

router = Router(name=__name__)

background_tasks = set()


@router.message(Command("study"))
async def cmd_study(message: Message, state: FSMContext) -> None:
    """Начать или продолжить обучение"""

    student_id = message.from_user.id
    async with session_factory() as session:
        student_repo = StudentRepository(session)
        course_repo = CourseRepository(session)
        group = await student_repo.get_student_group(student_id)
        course = await course_repo.read(group.course_id)
        learn_progress = await student_repo.get_learning_progress(student_id)
        if learn_progress is None:
            fist_module = course.modules[0]
            learn_progress = LearningProgress(
                student_id=student_id,
                course_id=group.course_id,
                started_at=current_datetime(),
                current_module_id=fist_module.id,
            )
            await student_repo.save_learning_progress(learn_progress)
    current_module_order = next(
        (
            order
            for order, module in enumerate(course.modules)
            if module.id == learn_progress.current_module_id
        ),
        None,
    )
    await state.update_data(
        group_id=group.id,
        course_id=group.course_id,
        current_module_id=learn_progress.current_module_id,
        module_order=current_module_order,
    )
    await message.answer(
        **Text(
            as_line(Bold(f"🎓 {course.title}"), end="\n\n"),
            as_line(BlockQuote(course.description)),
        ).as_kwargs(),
        reply_markup=get_modules_kb(
            modules=course.modules, current_module_id=learn_progress.current_module_id
        ),
    )


@router.callback_query(ModuleCbData.filter())
async def cb_module(query: CallbackQuery, callback_data: ModuleCbData, state: FSMContext) -> None:
    """Прохождение модуля"""

    await query.answer()
    data = await state.get_data()
    async with session_factory() as session:
        course_repo = CourseRepository(session)
        module = await course_repo.get_module(callback_data.module_id)
        if module.order > data["module_order"]:
            await query.answer(text="Материал недоступен!", show_alert=True)
            return
    await query.message.edit_text(
        **Text(
            as_line(Bold(f"📚 {module.title}"), end="\n\n"),
            as_line(BlockQuote(module.description)),
        ).as_kwargs(),
        reply_markup=get_module_study_kb(),
    )


async def generate_knowledge_test(
        bot: Bot, user_id: int, test_type: TestType, module: Module
) -> None:
    """Задача для фоновой генерации тестирования"""

    storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    state = FSMContext(storage=storage, key=storage_key)
    knowledge_test = await call_knowledge_tester(test_type, module)
    await state.update_data(knowledge_test=knowledge_test)
    await bot.send_message(
        user_id,
        **Text(
            as_line("Тестирование готово!", end="\n\n"),
            as_line(Bold(f"🧩 {knowledge_test.title}"), end="\n\n"),
            as_line("❓ Количество вопросов", "-", f"{len(knowledge_test.questions)}", sep=" "),
            as_line(
                "⏱️ Время выполнения",
                "-",
                Underline(f"{knowledge_test.estimated_time_minutes} минут"),
                sep=" ",
            ),
        ).as_kwargs(),
        reply_markup=get_start_test_kb(),
    )


@router.callback_query(ModuleStudyCbData.filter(F.action == ModuleAction.TAKE_TEST))
async def cb_take_test(query: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Прохождение тестирования по пройденной теории"""

    await query.answer()
    # test_type = random.choice([TestType.MULTIPLE_CHOICE, TestType.DETAILED_ANSWER])  # noqa: S311
    test_type = TestType.MULTIPLE_CHOICE
    data = await state.get_data()
    async with session_factory() as session:
        repo = CourseRepository(session)
        current_module = await repo.get_module(data["current_module_id"])
    await query.message.answer("🪄✨ Начинаю генерировать тестирование ...")
    task = asyncio.create_task(generate_knowledge_test(
        bot=bot,
        user_id=query.from_user.id,
        test_type=test_type,
        module=current_module
    ))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def get_multiply_choice_question_text(
        text: str, options: list[str], index: int, total: int
) -> Text:
    return Text(
        as_line(Bold(f"❓ Вопрос №{index + 1}")),
        as_line(
            "Пройдено", "-", Underline(f"{round((index / total) * 100, 2)}%"), sep=" "
        ),
        as_line(),
        as_line(text, end="\n\n"),
        as_numbered_section(Bold("Варианты ответа:"), *options)
    )


@router.callback_query(StartTestCbData.filter(F.action == "start"))
async def cb_start_test(query: CallbackQuery, state: FSMContext) -> None:
    """Начать тестирование"""

    await query.answer()
    data = await state.get_data()
    knowledge_test = data["knowledge_test"]
    question_index = 0
    first_question = knowledge_test.questions[question_index]
    content = get_multiply_choice_question_text(
        text=first_question.text,
        options=first_question.options,
        index=question_index,
        total=len(knowledge_test.questions)
    )
    if knowledge_test.test_type == TestType.MULTIPLE_CHOICE:
        await query.message.edit_text(
            **content.as_kwargs(), reply_markup=get_options_choice_kb(first_question.options)
        )
    else:
        await query.message.edit_text(**content.as_kwargs())
    await state.update_data(question_index=question_index, given_answers=[])
    await state.set_state(TestPassingForm.waiting_for_answer)


@router.callback_query(OptionChoiceCbData.filter(), TestPassingForm.waiting_for_answer)
async def process_option_choice(
        query: CallbackQuery, callback_data: OptionChoiceCbData, state: FSMContext
) -> None:
    """Обработка выбранного варианта ответа"""

    await query.answer()
    data = await state.get_data()
    question_index, knowledge_test, given_answers = (
        data["question_index"], data["knowledge_test"], data["given_answers"]
    )
    if question_index == len(knowledge_test.questions) - 1:
        result = check_multiple_choice_test(given_answers, knowledge_test)
        await save_test_result(
            student_id=query.from_user.id,
            module_id=data["current_module_id"],
            score=result.score
        )
        await query.message.edit_text(f"Результат {result.score} баллов")
        await state.update_data(
            question_index=None, knowledge_test=None, given_answers=None
        )
        await cmd_study(query.message, state)
        return
    question_index += 1
    given_answers.append(callback_data.index)
    question = knowledge_test.questions[question_index]
    content = get_multiply_choice_question_text(
        question.text, question.options, question_index, len(knowledge_test.questions)
    )
    await query.message.answer(
        **content.as_kwargs(), reply_markup=get_options_choice_kb(question.options)
    )
    await state.update_data(question_index=question_index, given_answers=given_answers)
    await state.set_state(TestPassingForm.waiting_for_answer)
