import random

import anyio
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import BlockQuote, Bold, Text, Underline, as_line

from src.core.commons import current_datetime
from src.core.entities.course import MultipleChoiceTest, TestResult, TestType
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

router = Router(name=__name__)


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


@router.callback_query(ModuleStudyCbData.filter(F.action == ModuleAction.TAKE_TEST))
async def cb_take_test(query: CallbackQuery, state: FSMContext) -> None:
    """Прохождение тестирования по пройденной теории"""

    await query.answer()
    # test_type = random.choice([TestType.MULTIPLE_CHOICE, TestType.DETAILED_ANSWER])  # noqa: S311
    test_type = TestType.MULTIPLE_CHOICE
    data = await state.get_data()
    async with session_factory() as session:
        repo = CourseRepository(session)
        current_module = await repo.get_module(data["current_module_id"])
    await query.message.answer("🪄✨ Начинаю генерировать тестирование ...")
    knowledge_test = await call_knowledge_tester(test_type, current_module)
    await state.update_data(knowledge_test=knowledge_test)
    await query.message.edit_text(
        **Text(
            as_line("Тестирование готово!", end="\n\n"),
            as_line(Bold(f"🧩 {knowledge_test.title}"), end="\n\n"),
            as_line(
                "❓ Количество вопросов", "-", f"{len(knowledge_test.questions)}", sep=" "
            ),
            as_line(
                "⏱️ Время выполнения",
                "-",
                Underline(f"{knowledge_test.estimated_time_minutes} минут"), sep=" ")
        ).as_kwargs(), reply_markup=get_start_test_kb()
    )


def get_question_text(text: str, current: int, total: int) -> Text:
    return Text(
        as_line(Bold(f"❓ Вопрос №{current}")),
        as_line(
            "Пройдено", "-", Underline(f"{round((current / total) * 100, 2)}%"), sep=" "
        ),
        as_line(),
        as_line(text),
    )


@router.callback_query(StartTestCbData.filter(F.action == "start"))
async def cb_start_test(query: CallbackQuery, state: FSMContext) -> None:
    """Начать тестирование"""

    await query.answer()
    data = await state.get_data()
    knowledge_test = data["knowledge_test"]
    question_index = 0
    first_question = knowledge_test.questions[question_index]
    content = get_question_text(
        first_question.text, question_index, len(knowledge_test.questions)
    )
    if knowledge_test.test_type == TestType.MULTIPLE_CHOICE:
        await query.message.edit_text(
            **content.as_kwargs(), reply_markup=get_options_choice_kb(first_question.options)
        )
    else:
        await query.message.edit_text(**content.as_kwargs())
    await state.update_data(question_index=question_index, given_answers=[])
    await state.set_state(TestPassingForm.waiting_for_answer)


def check_multiple_choice_test(
        given_answers: list[int], test: MultipleChoiceTest, passing_score: float = 61.0
) -> TestResult:
    total_points = 0
    max_points = sum(question.points for question in test.questions)
    for given_answer, question in zip(given_answers, test.questions, strict=False):
        if given_answer == question.correct_answer:
            total_points += question.points
    score = round(total_points / max_points, 2)
    is_passing = score >= passing_score
    return TestResult(score=score, is_passing=is_passing)


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
    given_answers.append(callback_data.index)
    if question_index == len(knowledge_test.questions) - 1:
        result = check_multiple_choice_test(given_answers, knowledge_test)
        await query.message.edit_text(f"Результат {result.score} баллов")
        await state.update_data(
            question_index=None, knowledge_test=None, given_answers=None
        )
        await cmd_study(query.message, state)
        return
    question_index += 1
    current_question = knowledge_test.questions[question_index]
    content = get_question_text(
        current_question.text, question_index, len(knowledge_test.questions)
    )
    await query.message.edit_text(
        **content.as_kwargs(), reply_markup=get_options_choice_kb(current_question.options)
    )
    await state.set_state(TestPassingForm.waiting_for_answer)
