from uuid import UUID

from ..core.entities.course import MultipleChoiceTest
from ..core.entities.student import LearningProgress
from ..infra.db.conn import session_factory
from ..infra.db.repos import CourseRepository, StudentRepository
from .dto import TestResult


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
        total_score = progress.total_score + result.score
        score_per_module = progress.score_per_module
        score_per_module.update({str(module_id): result.score})
        kwargs = {"total_score": total_score, "score_per_module": score_per_module}
        module_order = next(
            (order for order, module in enumerate(course.modules) if module.id == module_id),
            None,
        )
        if result.is_passed:
            module_order += 1
            if module_order <= len(course.modules):
                kwargs.update({"current_module_id": str(course.modules[module_order].id)})
        return await student_repo.update_learning_progress(student_id, **kwargs)
