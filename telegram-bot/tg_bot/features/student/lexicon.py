from aiogram.utils.formatting import BlockQuote, Bold, Text, Underline, as_line

MAIN_MENU_TEXT = Text(Bold("⚙️ Главное меню:"))
LIST_COURSES_TEXT = Text(Bold("📋 Список курсов:"))


def get_course_menu_text(title: str, description: str) -> Text:
    """Текст для главного меню курса"""

    return Text(
        Bold(f"📚 {title}"),
        as_line(),
        as_line(),
        as_line(Underline("📌 Описание:")),
        as_line(BlockQuote(f"{description}")),
        as_line(),
        as_line(),
        as_line(Bold("☰ Меню курса:"))
    )
