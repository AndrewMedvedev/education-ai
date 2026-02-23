import asyncio
import random

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

from src.app.schemas import TestResult
from src.app.services import (
    check_detailed_answer_test,
    check_multiple_choice_test,
    save_test_result,
)
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
from ..lexicon import (
    AI_FEEDBACK_TEMPLATE,
    CONFETTI_EFFECT_ID,
    COURSE_PREVIEW_TEMPLATE,
    DETAILED_ANSWER_QUESTION_TEMPLATE,
    FAIL_EFFECT_ID,
    FAILED_TEST_RESULT_TEMPLATE,
    FIRE_EFFECT_ID,
    GENERATED_TEST_TEMPLATE,
    GOOD_TEST_RESULT_TEMPLATE,
    GREAT_TEST_RESULT_TEMPLATE,
    MODULE_PREVIEW_TEMPLATE,
    MULTIPLE_CHOICE_QUESTION_TEMPLATE,
    PASSED_TEST_RESULT_TEMPLATE,
)
from ..setup import storage

MAX_TEST_SCORE = 100
PASSING_TEST_SCORE = 61
GOOD_TEST_SCORE = 81

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
    module_order = next(
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
        module_id=learn_progress.current_module_id,
        module_order=module_order,
    )
    await message.answer(
        COURSE_PREVIEW_TEMPLATE.format(title=course.title, description=course.description),
        reply_markup=get_modules_kb(
            modules=course.modules, current_module_id=learn_progress.current_module_id
        ),
    )


@router.callback_query(ModuleCbData.filter())
async def cb_module(query: CallbackQuery, callback_data: ModuleCbData, state: FSMContext) -> None:
    """Прохождение модуля"""

    await query.answer()
    data = await state.get_data()
    course_id, module_id = data["course_id"], data["module_id"]
    async with session_factory() as session:
        course_repo = CourseRepository(session)
        module = await course_repo.get_module(callback_data.module_id)
        if module.order > data["module_order"]:
            await query.answer(text="Материал недоступен!", show_alert=True)
            return
    await query.message.edit_text(
        MODULE_PREVIEW_TEMPLATE.format(title=module.title, description=module.description),
        reply_markup=get_module_study_kb(course_id, module_id),
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
        chat_id=user_id,
        text=GENERATED_TEST_TEMPLATE.format(
            title=knowledge_test.title,
            questions_count=len(knowledge_test.questions),
            estimated_time_minutes=knowledge_test.estimated_time_minutes,
        ),
        reply_markup=get_start_test_kb(),
    )


@router.callback_query(ModuleStudyCbData.filter(F.action == ModuleAction.TAKE_TEST))
async def cb_take_test(query: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Прохождение тестирования по пройденной теории"""

    await query.answer()
    test_type = random.choice([TestType.MULTIPLE_CHOICE, TestType.DETAILED_ANSWER])  # noqa: S311
    # test_type = TestType.MULTIPLE_CHOICE  # noqa: ERA001
    data = await state.get_data()
    async with session_factory() as session:
        repo = CourseRepository(session)
        module = await repo.get_module(data["module_id"])
    await query.message.answer("🪄✨ Начинаю генерировать тестирование (это займёт 30-60 сек) ...")
    task = asyncio.create_task(
        generate_knowledge_test(
            bot=bot, user_id=query.from_user.id, test_type=test_type, module=module
        )
    )
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


@router.callback_query(StartTestCbData.filter(F.action == "start"))
async def cb_start_test(query: CallbackQuery, state: FSMContext) -> None:
    """Начать тестирование"""

    await query.answer()
    data = await state.get_data()
    knowledge_test = data["knowledge_test"]
    question_index = 0
    first_question = knowledge_test.questions[question_index]
    if knowledge_test.test_type == TestType.MULTIPLE_CHOICE:
        await query.message.edit_text(
            MULTIPLE_CHOICE_QUESTION_TEMPLATE.format(
                number=question_index + 1,
                passed_percent=round(question_index / len(knowledge_test.questions) * 100, 2),
                text=first_question.text,
                options="\n".join([
                    f"{i + 1}) {option}" for i, option in enumerate(first_question.options)
                ]),
            ),
            reply_markup=get_options_choice_kb(first_question.options),
        )
    else:
        await query.message.edit_text(
            DETAILED_ANSWER_QUESTION_TEMPLATE.format(
                number=question_index + 1,
                passed_percent=round(question_index / len(knowledge_test.questions) * 100, 2),
                text=first_question.text,
                hint=first_question.hint,
            )
        )
    await state.update_data(question_index=question_index, given_answers=[])
    await state.set_state(TestPassingForm.waiting_for_answer)


async def show_test_result_message(message: Message, result: TestResult) -> None:
    """Показать сообщение с результатами тестирования"""

    data = {"score": result.score, "correct_answers_count": result.correct_answers_count}
    if not result.is_passed:
        await message.answer(
            text=FAILED_TEST_RESULT_TEMPLATE.format(**data),
            message_effect_id=FAIL_EFFECT_ID,
        )
    elif PASSING_TEST_SCORE <= result.score <= GOOD_TEST_SCORE:
        await message.answer(
            text=PASSED_TEST_RESULT_TEMPLATE.format(**data),
            message_effect_id=CONFETTI_EFFECT_ID,
        )
    elif GOOD_TEST_SCORE < result.score < MAX_TEST_SCORE:
        await message.answer(
            text=GOOD_TEST_RESULT_TEMPLATE.format(**data), message_effect_id=CONFETTI_EFFECT_ID
        )
    elif result.score == MAX_TEST_SCORE:
        await message.answer(
            text=GREAT_TEST_RESULT_TEMPLATE.format(**data), message_effect_id=FIRE_EFFECT_ID
        )
    if result.ai_feedback is not None:
        async with ChatActionSender.typing(chat_id=message.chat.id, bot=message.bot):
            await asyncio.sleep(1.2)
            await message.answer(AI_FEEDBACK_TEMPLATE.format(ai_feedback=result.ai_feedback))


@router.callback_query(OptionChoiceCbData.filter(), TestPassingForm.waiting_for_answer)
async def process_option_choice(
    query: CallbackQuery, callback_data: OptionChoiceCbData, state: FSMContext
) -> None:
    """Обработка выбранного варианта ответа"""

    await query.answer()
    data = await state.get_data()
    question_index, knowledge_test, given_answers = (
        data["question_index"],
        data["knowledge_test"],
        data["given_answers"],
    )
    if question_index == len(knowledge_test.questions) - 1:
        result = check_multiple_choice_test(given_answers, knowledge_test)
        await save_test_result(
            student_id=query.from_user.id,
            course_id=data["course_id"],
            module_id=data["module_id"],
            result=result,
        )
        await show_test_result_message(query.message, result)
        await state.clear()
        await asyncio.sleep(1.2)
        await query.message.answer("Нажмите /study, чтобы вернуться к изучению курса")
        return
    question_index += 1
    given_answers.append(callback_data.index)
    question = knowledge_test.questions[question_index]
    await query.message.edit_text(
        MULTIPLE_CHOICE_QUESTION_TEMPLATE.format(
            number=question_index + 1,
            passed_percent=round(question_index / len(knowledge_test.questions) * 100, 2),
            text=question.text,
            options="\n".join([f"{i + 1}) {option}" for i, option in enumerate(question.options)]),
        ),
        reply_markup=get_options_choice_kb(question.options),
    )
    await state.update_data(question_index=question_index, given_answers=given_answers)
    await state.set_state(TestPassingForm.waiting_for_answer)


@router.message(TestPassingForm.waiting_for_answer, F.text)
async def process_detailed_answer(message: Message, state: FSMContext) -> None:
    """Обработка развёрнутого ответа"""

    data = await state.get_data()
    question_index, knowledge_test, given_answers = (
        data["question_index"],
        data["knowledge_test"],
        data["given_answers"],
    )
    if question_index == len(knowledge_test.questions) - 1:
        await message.answer("🤖 Начинаю проверку тестирования ...")
        result = await check_detailed_answer_test(given_answers, knowledge_test)
        await save_test_result(
            student_id=message.from_user.id,
            course_id=data["course_id"],
            module_id=data["module_id"],
            result=result,
        )
        await show_test_result_message(message, result)
        await state.clear()
        await asyncio.sleep(1.2)
        await message.answer("Нажмите /study, чтобы вернуться к изучению курса")
        return
    question_index += 1
    given_answers.append(message.text.strip())
    question = knowledge_test.questions[question_index]
    await message.edit_text(
        DETAILED_ANSWER_QUESTION_TEMPLATE.format(
            number=question_index + 1,
            passed_percent=round(question_index / len(knowledge_test.questions) * 100, 2),
            text=question.text,
            hint=question.hint,
        )
    )
    await state.update_data(question_index=question_index, given_answers=given_answers)
    await state.set_state(TestPassingForm.waiting_for_answer)
