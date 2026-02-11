from datetime import datetime

from aiogram.utils.formatting import (
    BlockQuote,
    Bold,
    Italic,
    Spoiler,
    Text,
    Underline,
    as_line,
    as_marked_section,
)


def get_my_progress_text(
        full_name: str, login: str, group_title: str, created_at: datetime
) -> Text:
    return Text(
        as_marked_section(
            Bold("👤 Профиль студента:"),
            *[
                Text("ФИО: ", Italic(f"{full_name}")),
                Text("Группа: ", Underline(f"{group_title}")),
                Text("Логин: ", Spoiler(f"{login}")),
                f"Добавлен на курс: {created_at.strftime('%d.%m.%Y %H:%M')}"
            ],
            marker="• "
        )
    )


def get_current_module_text(title: str, description: str, order: int, total: int) -> Text:
    return Text(
        Bold("📗 Текущий модуль:"),
        as_line(Underline(f"{title}")),
        as_line(),
        as_line(),
        as_line(Italic("📌 Описание:")),
        as_line(BlockQuote(f"{description}")),
        as_line(),
        as_line(),
        as_line(Bold("📈 Пройдено:"), f"{order + 1}/{total}"),
    )


def get_module_menu_text(title: str) -> Text:
    return Text(
        Bold("☰ Меню:"),
        as_line(Underline(f"{title}")),
    )
