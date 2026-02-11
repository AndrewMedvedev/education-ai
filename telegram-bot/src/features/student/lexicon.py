from aiogram.utils.formatting import Bold, Text, Underline, as_line

MAIN_MENU_TEXT = Text(Bold("⚙️ Главное меню:"))
LIST_COURSES_TEXT = Text(Bold("📋 Список курсов:"))


def get_course_menu_text(title: str) -> Text:
    """Текст для главного меню курса"""

    return Text(
        Bold("☰ Меню курса: "),
        as_line("📚", Underline(f"{title}"), sep=" ")
    )
