# pyright: reportArgumentType=false

from typing import Annotated

from fastapi import Depends

from src.shared.dependencies.database import DBSession

from ..agents.external_agents import editor, interviewer, mentor, practicer, tester
from ..infra.services import course_client
from .base import ChatRepoDep, LessonRepoDep, PracticeRepoDep


def get_interviewer_agent(session: DBSession, repo: ChatRepoDep) -> interviewer.InterviewerAgent:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return interviewer.InterviewerAgent(repo=repo, session=session, client=course_client)


def get_editor_agent(session: DBSession, repo: ChatRepoDep) -> editor.EditorAgent:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return editor.EditorAgent(repo=repo, session=session, client=course_client)


def get_mentor_agent(session: DBSession, repo: ChatRepoDep) -> mentor.MentorAgent:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return mentor.MentorAgent(repo=repo, session=session, client=course_client)


def get_practicer_agent(
    session: DBSession,
    practice_repo: PracticeRepoDep,
    lesson_repo: LessonRepoDep,
) -> practicer.PracticerAgent:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return practicer.PracticerAgent(
        practice_repo=practice_repo,
        session=session,
        lesson_repo=lesson_repo,
        client=course_client,
    )


def get_tester_agent(
    session: DBSession,
    practice_repo: PracticeRepoDep,
    lesson_repo: LessonRepoDep,
) -> tester.TesterAgent:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return tester.TesterAgent(
        practice_repo=practice_repo,
        session=session,
        lesson_repo=lesson_repo,
        client=course_client,
    )


InterviewerAgentDep = Annotated[interviewer.InterviewerAgent, Depends(get_interviewer_agent)]

EditorAgentDep = Annotated[editor.EditorAgent, Depends(get_editor_agent)]

MentorAgentDep = Annotated[mentor.MentorAgent, Depends(get_mentor_agent)]

TesterAgentDep = Annotated[tester.TesterAgent, Depends(get_tester_agent)]

PracticeAgentDep = Annotated[practicer.PracticerAgent, Depends(get_practicer_agent)]
