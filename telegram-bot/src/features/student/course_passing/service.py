import logging
from uuid import UUID

from src.core.database import session_factory
from src.features.course.schemas import TestAssignment

from . import repository
from .schemas import Submission

logger = logging.getLogger(__name__)


def _is_answers_correct(given_answers: list[int], correct_answers: list[int]) -> bool:
    """Проверка полученных ответов на правильность"""

    return (
            len(given_answers) == len(correct_answers) and
            set(given_answers) == set(correct_answers)
    )


async def pass_test_assignment(
        practice_id: UUID,
        user_id: int,
        test_answers: list[list[int]],
        assignment: TestAssignment,
) -> Submission:
    if len(test_answers) != len(assignment.questions):
        raise ValueError(
            "Test answers must have same length as the number of questions!"
        )
    score = 0
    for question_answers, question in zip(test_answers, assignment.questions, strict=False):
        if _is_answers_correct(question_answers, question.correct_answers):
            score += question.points
    is_passed = score >= assignment.passing_score
    async with session_factory() as session:
        submission = Submission(
            practice_id=practice_id,
            user_id=user_id,
            score=score,
            is_passed=is_passed,
        )
        await repository.add_submission(session, submission)
    return submission
