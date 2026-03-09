import logging
from uuid import UUID

from ..core.commons import current_datetime
from ..core.entities.course import DetailedAnswerTest, MultipleChoiceTest
from ..core.entities.student import LearningProgress
from ..infra.ai.agents.assignment_checker import call_assignment_checker
from ..infra.ai.agents.test_checker import call_test_checker
from ..infra.db.conn import session_factory
from ..infra.db.repos import CourseRepository, StudentRepository
from ..utils.docs_processing import convert_document_to_md
from .schemas import AssignmentResult, TestResult

# Максимальное количество попыток перепрохождения тестирования
MAX_TEST_ATTEMPTS = 3

logger = logging.getLogger(__name__)


def check_multiple_choice_test(
    given_answers: list[int], test: MultipleChoiceTest, passing_score: float = 61.0
) -> TestResult:
    """Проверка тестирования с выбором варианта ответа"""

    total_points, correct_answers_count = 0, 0
    max_points = sum(question.points for question in test.questions)
    for given_answer, question in zip(given_answers, test.questions, strict=False):
        if given_answer == question.correct_answer:
            correct_answers_count += 1
            total_points += question.points
    score = round((total_points / max_points) * 100, 2)
    is_passed = score >= passing_score
    return TestResult(
        score=score, correct_answers_count=correct_answers_count, is_passed=is_passed
    )


async def save_test_result(student_id: int, result: TestResult) -> LearningProgress:
    """Сохранение и обновление прогресса обучения на основе результата тестирования"""

    async with session_factory() as session:
        student_repo = StudentRepository(session)
        progress = await student_repo.get_learning_progress(student_id)
        progress.increment_test_score(result.score)
        await student_repo.refresh_learning_progress(progress)
        return progress


async def check_detailed_answer_test(
        given_answers: list[str], test: DetailedAnswerTest
) -> TestResult:
    """Проверка тестирования с развёрнутыми вариантами ответа с помощью AI"""

    return await call_test_checker(given_answers, test)


async def submit_file_upload_assignment(
        student_id: int, module_id: UUID, file_data: bytes, file_extension: str
) -> AssignmentResult:
    """Сдать задание с загрузкой файла на проверку"""

    async with session_factory() as session:
        course_repo = CourseRepository(session)
        student_repo = StudentRepository(session)
        task = await student_repo.get_task(student_id, module_id)
        if file_extension not in task.assignment.allowed_extensions:
            logger.warning(
                "Student submit not allowed extension, extension - `%s`!", file_extension
            )
            raise ValueError(
                f"Student submit not allowed extension, extension - `{file_extension}`!"
            )
        if file_extension == ".md":
            md_text = file_data.decode("utf-8")
        else:
            md_text = convert_document_to_md(file_data, file_extension=file_extension)
        task.add_submission({"file_extension": file_extension, "md_text": md_text})
        await student_repo.refresh_task(task)
        result = await call_assignment_checker(task.assignment, task.submission_data)
        progress = await student_repo.get_learning_progress(student_id)
        progress.increment_assignment_score(result.score)
        course = await course_repo.read(progress.course_id)
        current_module = next(
            (module for module in course.modules if module.id == progress.current_module_id), None
        )
        if (current_module.order + 1) <= len(course.modules):
            next_module = course.modules[current_module.order + 1]
            progress.switch_to_next_module(next_module.id)
        await student_repo.refresh_learning_progress(progress)
    return result


async def check_daily_chat_limit(user_id: int) -> bool:
    """Проверка ежедневного лимита сообщений"""

    async with session_factory() as session:
        student_repo = StudentRepository(session)
        chat_limit = await student_repo.get_or_create_daily_chat_limit(
            user_id, today_date=current_datetime().date()
        )
        if chat_limit.is_reached:
            return False
        chat_limit.increment_count()
        await student_repo.refresh_daily_chat_limit(chat_limit)
        return True
