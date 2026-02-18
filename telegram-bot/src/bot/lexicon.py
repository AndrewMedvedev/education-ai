from aiogram.utils.formatting import Bold, BotCommand, Text, as_line, as_marked_section

CONFETTI_EFFECT_ID = "5104841245755180586"

# Командное меню студента
STUDENT_CMD_MENU_TEXT = Text(
    as_marked_section(
        Bold("⚙️ Командное меню:"),
        as_line(BotCommand("study"), "-", "прохождение курса", sep=" "),
        as_line(
            BotCommand("profile"),
            "-",
            "мой профиль (информация о студенте, успеваемость, ...)",
            sep=" "
        ),
        as_line(BotCommand("info"), "-", "информация о боте", sep=" ")
        )
)
