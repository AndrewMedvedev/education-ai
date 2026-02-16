from .ai_agent.agents.interviewer import UserContext, interviewer_agent


async def start_interview_with_teacher(
        user_id: int, course_title: str, uploaded_documents: list[str] | None = None
) -> str:
    """Начинает интервью с AI - агентом интервьюером.

    :param user_id: Идентификатор пользователя.
    :param course_title: Название курса.
    :param uploaded_documents: Имена загруженных документов.
    :returns: Сгенерированный первый вопрос.
    """

    prompt_template = f"""\
    **Название курса:** {course_title}
    **Загруженные материалы:** {
        "; ".join(uploaded_documents) if uploaded_documents
        else "Преподаватель не загрузил материалы"
    }

    Проанализируй материалы (если они есть), продумай интервью, после чего задай первый вопрос,
    чтобы начать интервью.
    """
    thread_id = f"interview-with-teacher-{user_id}"
    result = await interviewer_agent.ainvoke(
        {"messages": [("human", prompt_template)]},
        config={"configurable": {"thread_id": thread_id}},
        context=UserContext(user_id=user_id),
    )
    return result["messages"][-1].content
