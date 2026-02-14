from app.core.entities.course import (
    AnyAssignment,
    AnyContentBlock,
    AssignmentType,
    ContentType,
    Module,
)


def get_assignment_context(assignment: AnyAssignment) -> str:
    context = f"## Практическое задание\n**Тип задания**: {assignment.assignment_type}\n"
    match assignment.assignment_type:
        case AssignmentType.TEST:
            context += "Список вопросов\n"
            for question in assignment.questions:
                context += f"Вопрос: {question.text}"
                for i, option in enumerate(question.options):
                    context += f" - {i}. {option}\n"
    context += "\n"
    return context


def get_content_blocks_context(content_blocks: list[AnyContentBlock]) -> str:
    context = "## Теоретический материал\n\n"
    for content_block in content_blocks:
        context += f"### {content_block.content_type.value}\n"
        match content_block.content_type:
            case ContentType.TEXT:
                context += f"{content_block.md_content}\n\n"
            case ContentType.VIDEO:
                context += (
                    f"Платформа: {content_block.platform}\n"
                    f"Ссылка на видео: {content_block.url}\n"
                    f"Название видео: {content_block.title}\n"
                    "Вопросы для обсуждения:\n"
                    f" - {'\n - '.join(content_block.discussion_questions)}"
                )
            case ContentType.QUIZ:
                context += (
                    "Вопросы для самопроверки:\n"
                    f" - {'\n - '.join([
                        f"вопрос: {question}; ответ: {answer}"
                        for question, answer in content_block.questions
                    ])}"
                )
            case ContentType.PROGRAM_CODE:
                context = (
                    f"```{content_block.language}\n{content_block.code}\n```\n\n"
                    f"Объяснение: {content_block.explanation}"
                )
            case ContentType.MERMAID:
                context += (
                    f"Название диаграммы: {content_block.title}\n"
                    f"Диаграмма:\n{content_block.mermaid_code}\n"
                    f"Объяснение: {content_block.explanation}"
                )
        context += "\n\n"
    return context


def get_module_context(
        module: Module,
        include_content_blocks: bool = True,
        include_assignment: bool = False
) -> str:
    """Получение LLM-friendly контекста текущего модуля в Markdown формате."""

    context = (
        f"# Модуль [{module.order}]: '{module.title}'\n"
        f"**Описание**: {module.description}\n\n"
        "**Цели обучения**:\n"
        f" - {f'{module.learning_objectives}'}"
        "\n\n"
    )
    if module.content_blocks and include_content_blocks:
        context += get_content_blocks_context(module.content_blocks)
    if include_assignment and module.assignment is not None:
        context += get_assignment_context(module.assignment)
    return context
