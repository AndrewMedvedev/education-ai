from aiogram.utils.formatting import Bold, Text, Underline, as_line


def get_course_menu_text(title: str) -> Text:
    """Текст для главного меню курса"""

    return Text(
        Bold("☰ Меню курса: "),
        as_line("📚", Underline(f"{title}"), sep=" ")
    )
