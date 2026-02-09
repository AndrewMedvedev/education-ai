import logging
from uuid import UUID

from src.features.course.schemas import TestAssignment

from .schemas import AssignmentResult

logger = logging.getLogger(__name__)


def _is_answers_correct(given_answers: list[int], correct_answers: list[int]) -> bool:
    """Проверка полученных ответов на правильность"""

    return (
            len(given_answers) == len(correct_answers) and
            set(given_answers) == set(correct_answers)
    )


async def take_test_assignment(
        module_id: UUID,
        user_id: int,
        test_answers: list[list[int]],
        assignment: TestAssignment,
) -> AssignmentResult:
    if len(test_answers) != len(assignment.questions):
        raise ValueError(
            "Test answers must have same length as the number of questions!"
        )
    assignment_score = 0
    for question_answers, question in zip(test_answers, assignment.questions, strict=False):
        if _is_answers_correct(question_answers, question.correct_answers):
            assignment_score += question.points
    is_passing = assignment_score >= assignment.passing_score
    return AssignmentResult(score=assignment_score, is_passing=is_passing)
