# Модуль для сдачи практических заданий

import logging
from uuid import UUID

from src.core.database import session_factory
from src.features.course.schemas import (
    FileUploadAssignment,
    GitHubAssignment,
    TestAssignment,
    TestQuestion,
)

from .. import repository
from ..schemas import Submission

logger = logging.getLogger(__name__)


def _calculate_score(given_answers: list[list[int]], test_questions: list[TestQuestion]) -> float:
    score = 0
    for question_answers, test_question in zip(given_answers, test_questions, strict=False):
        if len(question_answers) == len(test_question.correct_answers) and \
                set(question_answers) == set(test_question.correct_answers):
            score += test_question.points
    return score


async def pass_test_assignment(
        practice_id: UUID,
        user_id: int,
        given_answers: list[list[int]],
        assignment: TestAssignment,
) -> Submission:
    if len(given_answers) != len(assignment.questions):
        raise ValueError(
            "Test answers must have same length as the number of questions!"
        )
    score = _calculate_score(given_answers, assignment.questions)
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


async def pass_assignment_with_file_upload(
        practice_id: UUID,
        user_id: int,
        file_id: str,
        file_name: str,
        assignment: FileUploadAssignment,
) -> Submission:
    ...


async def pass_github_assignment(
        practice_id: UUID,
        user_id: int,
        repo_url: str,
        assignment: GitHubAssignment,
) -> Submission:
    ...
