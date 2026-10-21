# pyright: reportArgumentType=false

from typing import Annotated

from fastapi import Depends
from langgraph.graph.state import CompiledStateGraph

from src.courses.agents.course_generator.serializer import checkpointer
from src.courses.agents.course_generator.subagents.course_builder import (
    CourseAgent,
    CourseAgentState,
    build_course_graph,
)
from src.courses.agents.course_generator.subagents.lesson_builder import (
    LessonAgent,
    LessonAgentState,
    build_lesson_graph,
)
from src.courses.agents.course_generator.subagents.module_builder import (
    ModuleAgent,
    ModuleAgentState,
    build_module_graph,
)
from src.courses.agents.course_generator.subagents.protocols import ReasonerAgent, TheoryAgent
from src.courses.agents.course_generator.subagents.reasoner import reasoner_agent
from src.courses.agents.course_generator.subagents.theorist import call_theory_agent
from src.courses.agents.course_generator.tools import (
    generate_course_structure,
    generate_lesson_structure,
    generate_module_structure,
)
from src.courses.agents.external_agents import editor, interviewer, mentor, practicer, tester
from src.courses.agents.prompts import (
    COURSE_INTERVIEWER_PROMPT,
    LESSON_INTERVIEWER_PROMPT,
    MODULE_INTERVIEWER_PROMPT,
)
from src.courses.agents.tools import (
    send_course_for_generation,
    send_lesson_for_generation,
    send_module_for_generation,
)
from src.courses.infra.database.repos.lesson import SqlLessonRepository
from src.courses.infra.database.repos.module import SqlModuleRepository
from src.courses.infra.services import course_client
from src.shared.dependencies.database import DBSession, TransactionDep

from .base import (
    ChatRepoDep,
    CourseRepoDep,
    LessonRepoDep,
    PracticeRepoDep,
    VectorRepoDep,
)


def get_course_interviewer_agent(
    session: DBSession,
    repo: ChatRepoDep,
) -> interviewer.InterviewerAgent:
    return interviewer.InterviewerAgent(
        repo=repo,
        session=session,
        client=course_client,
        system_prompt=COURSE_INTERVIEWER_PROMPT,
        tools={
            "generate_course_structure": generate_course_structure,
            "send_course_for_generation": send_course_for_generation,
        },
        tool_limits={
            "generate_course_structure": 1,
            "send_course_for_generation": 1,
        },
    )


def get_module_interviewer_agent(
    session: DBSession,
    repo: ChatRepoDep,
) -> interviewer.InterviewerAgent:
    return interviewer.InterviewerAgent(
        repo=repo,
        session=session,
        client=course_client,
        system_prompt=MODULE_INTERVIEWER_PROMPT,
        tools={
            "generate_module_structure": generate_module_structure,
            "send_module_for_generation": send_module_for_generation,
        },
        tool_limits={
            "generate_module_structure": 1,
            "send_module_for_generation": 1,
        },
    )


def get_lesson_interviewer_agent(
    session: DBSession,
    repo: ChatRepoDep,
) -> interviewer.InterviewerAgent:
    return interviewer.InterviewerAgent(
        repo=repo,
        session=session,
        client=course_client,
        system_prompt=LESSON_INTERVIEWER_PROMPT,
        tools={
            "generate_lesson_structure": generate_lesson_structure,
            "send_lesson_for_generation": send_lesson_for_generation,
        },
        tool_limits={
            "generate_lesson_structure": 1,
            "send_lesson_for_generation": 1,
        },
    )


CourseInterviewerAgentDep = Annotated[
    interviewer.InterviewerAgent, Depends(get_course_interviewer_agent)
]
ModuleInterviewerAgentDep = Annotated[
    interviewer.InterviewerAgent, Depends(get_module_interviewer_agent)
]
LessonInterviewerAgentDep = Annotated[
    interviewer.InterviewerAgent, Depends(get_lesson_interviewer_agent)
]


def get_editor_agent(session: DBSession, repo: ChatRepoDep) -> editor.EditorAgent:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return editor.EditorAgent(repo=repo, session=session, client=course_client)


def get_mentor_agent(session: DBSession, repo: ChatRepoDep) -> mentor.MentorAgent:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return mentor.MentorAgent(repo=repo, session=session, client=course_client)


def get_practicer_agent(
    practice_repo: PracticeRepoDep,
    lesson_repo: LessonRepoDep,
    transaction: TransactionDep,
) -> practicer.PracticerAgent:
    return practicer.PracticerAgent(
        practice_repo=practice_repo,
        lesson_repo=lesson_repo,
        transaction=transaction,
        client=course_client,
    )


def get_tester_agent(
    practice_repo: PracticeRepoDep,
    lesson_repo: LessonRepoDep,
    transaction: TransactionDep,
) -> tester.TesterAgent:
    return tester.TesterAgent(
        practice_repo=practice_repo,
        lesson_repo=lesson_repo,
        transaction=transaction,
        client=course_client,
    )


def get_theory_agent() -> TheoryAgent:
    return call_theory_agent


def get_reasoner_agent() -> ReasonerAgent:
    return reasoner_agent


TheoryAgentDep = Annotated[TheoryAgent, Depends(get_theory_agent)]
ReasonerAgentDep = Annotated[ReasonerAgent, Depends(get_reasoner_agent)]


def get_lesson_agent(
    vector_repo: VectorRepoDep,
    theory_agent: TheoryAgentDep,
) -> CompiledStateGraph[LessonAgentState]:
    from src.courses.infra.tasks import index_lesson  # noqa: PLC0415

    agent = LessonAgent(
        client=course_client,
        lesson_repo=SqlLessonRepository,
        vector_repo=vector_repo,
        theory_agent=theory_agent,
        index_lesson=index_lesson,
    )
    return build_lesson_graph(agent=agent, checkpointer=checkpointer)


LessonAgentDep = Annotated[CompiledStateGraph[LessonAgentState], Depends(get_lesson_agent)]


def get_module_agent(
    lesson_agent: LessonAgentDep,
) -> CompiledStateGraph[ModuleAgentState]:
    agent = ModuleAgent(
        client=course_client,
        module_repo=SqlModuleRepository,
        lesson_agent=lesson_agent,
    )
    return build_module_graph(agent=agent, checkpointer=checkpointer)


ModuleAgentDep = Annotated[CompiledStateGraph[ModuleAgentState], Depends(get_module_agent)]


def get_course_agent(
    session: DBSession,
    repo: CourseRepoDep,
    module_agent: ModuleAgentDep,
    reasoner_agent: ReasonerAgentDep,
) -> CompiledStateGraph[CourseAgentState]:
    agent = CourseAgent(
        session=session,
        client=course_client,
        repo=repo,
        module_agent=module_agent,
        reasoner_agent=reasoner_agent,
    )
    return build_course_graph(agent=agent, checkpointer=checkpointer)


CourseAgentDep = Annotated[CompiledStateGraph[CourseAgentState], Depends(get_course_agent)]


EditorAgentDep = Annotated[editor.EditorAgent, Depends(get_editor_agent)]

MentorAgentDep = Annotated[mentor.MentorAgent, Depends(get_mentor_agent)]

TesterAgentDep = Annotated[tester.TesterAgent, Depends(get_tester_agent)]

PracticeAgentDep = Annotated[practicer.PracticerAgent, Depends(get_practicer_agent)]
