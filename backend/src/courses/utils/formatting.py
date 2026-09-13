from ..domain.entities import (
    AnyAssignment,
    AnyContentBlock,
    AssignmentType,
    ContentType,
    Lesson,
)


def get_assignment_context(assignment: AnyAssignment) -> str:
    """Получает assignment context, чтобы вызывающий код работал через единый интерфейс."""
    assignment_type_map = {
        AssignmentType.FILE_UPLOAD: "Задание с загрузкой файла",
        AssignmentType.GITHUB: "Задание на платформе GitHub",
    }
    context = (
        f"## Практическое задание: '{assignment.title}'\n"
        f"**{assignment_type_map[assignment.assignment_type]}**\n\n"
    )
    match assignment.assignment_type:
        case AssignmentType.FILE_UPLOAD:
            context += (
                "### Постановка задачи\n"
                f"{assignment.description}\n\n"
                "### Инструкция по оформлению\n"
                f"{assignment.submission_instructions}\n\n"  # type: ignore  # ruff: ignore[blanket-type-ignore]
            )
    context += f"### Критерии оценивания{'\n - '.join(assignment.evaluation_criteria)}"
    context += "\n"
    return context


def get_content_blocks_context(content_blocks: list[AnyContentBlock]) -> str:
    """Получает content blocks context, чтобы вызывающий код работал через единый интерфейс."""
    context = "## Теоретический материал\n\n"
    for content_block in content_blocks:
        context += f"### {content_block.content_type.value}\n"
        match content_block.content_type:
            case ContentType.TEXT:
                context += f"{content_block.md_content}\n\n"  # type: ignore  # ruff: ignore[blanket-type-ignore]
            case ContentType.QUIZ:
                context += (
                    "Вопросы для самопроверки:\n"
                    f" - {
                        '\n - '.join([
                            f'вопрос: {item.question}; ответ: {item.answer}'
                            for item in content_block.questions  # pyright: ignore[reportAttributeAccessIssue]
                        ])
                    }"
                )
            case ContentType.PROGRAM_CODE:
                context += (
                    f"```{content_block.language}\n{content_block.code}\n```\n\n"  # type: ignore  # ruff: ignore[blanket-type-ignore]
                    f"Объяснение: {content_block.explanation}"  # type: ignore  # ruff: ignore[blanket-type-ignore]
                )
            case ContentType.MERMAID:
                context += (
                    f"Название диаграммы: {content_block.title}\n"  # type: ignore  # ruff: ignore[blanket-type-ignore]
                    f"Диаграмма:\n{content_block.md_content}\n"  # type: ignore  # ruff: ignore[blanket-type-ignore]
                    f"Объяснение: {content_block.explanation}"  # type: ignore  # ruff: ignore[blanket-type-ignore]
                )
            case (
                ContentType.MATH_FORMULA
                | ContentType.CHEMICAL_FORMULA
                | ContentType.MUSICAL_NOTATION
            ):
                context += (
                    f"Формула:\n{content_block.formula}\n"  # type: ignore  # ruff: ignore[blanket-type-ignore]
                    f"Объяснение: {content_block.explanation}"  # type: ignore  # ruff: ignore[blanket-type-ignore]
                )

        context += "\n\n"
    return context


def get_lesson_context(
    lesson: Lesson,
    include_content_blocks: bool = True,
) -> str:
    """Получение LLM-friendly контекста текущего урока в Markdown формате."""

    context = (
        f"# Урок [{lesson.order}]: '{lesson.title}'\n"
        f"**Описание**: {lesson.description}\n\n"
        "**Цели обучения**:\n"
        f" - {f'{lesson.learning_objectives}'}"
        "\n\n"
    )
    if lesson.content_blocks and include_content_blocks:
        context += get_content_blocks_context(lesson.content_blocks)  # type: ignore  # ruff: ignore[blanket-type-ignore]

    return context
