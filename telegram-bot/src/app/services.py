from uuid import UUID

from ..core.entities.course import DetailedAnswerTest, MultipleChoiceTest
from ..core.entities.student import LearningProgress
from ..infra.ai.agents.test_checker import call_test_checker
from ..infra.db.conn import session_factory
from ..infra.db.repos import CourseRepository, StudentRepository
from .schemas import TestResult

# Максимальное количество попыток перепрохождения тестирования
MAX_TEST_ATTEMPTS = 3


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


async def save_test_result(
    student_id: int, course_id: UUID, module_id: UUID, result: TestResult
) -> LearningProgress:
    """Сохранение результатов тестирования в прогресс обучения"""

    async with session_factory() as session:
        course_repo = CourseRepository(session)
        student_repo = StudentRepository(session)
        course = await course_repo.read(course_id)
        progress = await student_repo.get_learning_progress(student_id)
        progress.increment_score(result.score)
        if result.is_passed:
            module_order = next(
                (module.order for module in course.modules if module.id == module_id),
                None,
            )
            if module_order is not None and module_order + 1 <= len(course.modules):
                next_module = course.modules[module_order + 1]
                progress.switch_to_next_module(next_module.id)
        await student_repo.refresh_learning_progress(progress)
        return progress


async def check_detailed_answer_test(
    given_answers: list[str], test: DetailedAnswerTest, passing_score: float = 61.0
) -> TestResult:
    """Проверка тестирования с развёрнутыми вариантами ответа с помощью AI"""

    max_points = sum(question.points for question in test.questions)
    result = await call_test_checker(given_answers, test)
    score = round((result.total_points / max_points) * 100, 2)
    is_passed = score >= passing_score
    return TestResult(
        score=score,
        correct_answers_count=result.correct_answers_count,
        is_passed=is_passed,
        ai_feedback=result.feedback,
    )
