from uuid import UUID

from ..core.entities.course import MultipleChoiceTest
from ..core.entities.student import LearningProgress
from ..infra.db.conn import session_factory
from ..infra.db.repos import StudentRepository
from .dtos import TestResult


def check_multiple_choice_test(
        given_answers: list[int], test: MultipleChoiceTest, passing_score: float = 61.0
) -> TestResult:
    total_points = 0
    max_points = sum(question.points for question in test.questions)
    for given_answer, question in zip(given_answers, test.questions, strict=False):
        if given_answer == question.correct_answer:
            total_points += question.points
    score = round((total_points / max_points) * 100, 2)
    is_passing = score >= passing_score
    return TestResult(score=score, is_passing=is_passing)


async def save_test_result(student_id: int, module_id: UUID, score: float) -> LearningProgress:
    async with session_factory() as session:
        repo = StudentRepository(session)
        progress = await repo.get_learning_progress(student_id)
        total_score = progress.total_score + score
        score_per_module = progress.score_per_module
        score_per_module.update({module_id: score})
        return await repo.update_learning_progress(
            student_id, total_score=total_score, score_per_module=score_per_module
        )
