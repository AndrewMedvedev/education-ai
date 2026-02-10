# Заготовленные шаблоны сообщений

from aiogram.utils.formatting import (
    BlockQuote,
    Bold,
    Italic,
    Text,
    Underline,
    as_line,
    as_marked_section,
    as_section,
)


def get_course_list_text(total: int, published: int) -> Text:
    """Шаблон текста сообщения для просмотра списка курсов.

    :param total: Общее количество курсов.
    :param published: Количество опубликованных курсов.
    """
    return Text(
        Bold("🎓 Список курсов"),
        as_line(),
        as_line(),
        as_line(f"🔢 Общее количество: {total}"),
        as_line(f"📢 Опубликовано: {published}"),
    )


def get_course_preview_text(
        title: str, description: str, learning_objectives: list[str]
) -> Text:
    """Текст сообщения с деталями курса.

    :param title: Название курса
    :param description: Описание курса.
    :param learning_objectives: Цели обучения.
    """

    return Text(
        Bold(f"🎓 {title}"),
        as_line(),
        as_line(),
        as_line(Underline("📌 Описание:")),
        as_line(BlockQuote(f"{description}")),
        as_line(),
        as_marked_section(
            Underline("🎯 Цели обучения:"), *learning_objectives, marker="✓ "
        )
    )


def get_course_details_text(
        title: str,
        description: str,
        learning_objectives: list[str],
        module_titles: list[str],
) -> Text:
    tree_lines = []
    for i, mod_title in enumerate(module_titles, 1):
        is_last = i == len(module_titles)
        prefix = "└── " if is_last else "├── "
        connector = "    " if is_last else "│   "
        line = Text(
            Italic(connector) if i > 1 else Text(),
            Bold(prefix),
            f"Модуль {i:02d}  •  {mod_title.strip()}",
        )
        tree_lines.append(line)

    modules_tree = as_section(
        Underline("📂 Структура курса:"),
        as_line(),
        *tree_lines,
        as_line(),
        Italic(f"Всего модулей: {len(module_titles)}"),
    )
    return Text(
        Bold(f"🎓 {title}"),
        as_line(),
        as_line(),
        as_line(Underline("📌 Описание:")),
        as_line(BlockQuote(f"{description}")),
        as_line(),
        as_marked_section(Underline("🎯 Цели обучения:"), *learning_objectives, marker="✓ "),
        as_line(),
        as_line("─" * 40),
        as_line(),
        modules_tree,
    )


def get_module_preview_text(order: int, title: str, description: str) -> Text:
    return Text(
        as_line("🆔", Bold(f"{order}"), sep=" "),
        as_line(),
        as_line(),
        as_line("##############################################"),
        Bold(f"📚 {title}"),
        as_line(),
        as_line(),
        as_line(Underline("📌 Описание:")),
        as_line(BlockQuote(f"{description}"))
    )
