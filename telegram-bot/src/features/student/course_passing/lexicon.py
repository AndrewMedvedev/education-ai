from datetime import datetime

from aiogram.utils.formatting import Bold, Italic, Spoiler, Text, Underline, as_marked_section


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
