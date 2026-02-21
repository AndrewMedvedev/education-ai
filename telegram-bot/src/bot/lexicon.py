from aiogram.utils.formatting import Bold, BotCommand, Text, as_line, as_marked_section

# Эффект сообщения с конфетти
CONFETTI_EFFECT_ID = "5104841245755180586"

# Командное меню студента
STUDENT_CMD_MENU_TEXT = Text(
    as_marked_section(
        Bold("⚙️ Командное меню:"),
        as_line(BotCommand("/study"), "-", "прохождение курса", sep=" "),
        as_line(
            BotCommand("/profile"),
            "-",
            "мой профиль (информация о студенте, успеваемость, ...)",
            sep=" "
        ),
        as_line(BotCommand("/chat", "-", "чат с AI ассистентом"), sep=" "),
        as_line(BotCommand("/info"), "-", "информация о боте", sep=" ")
        )
)

# Сообщение для превью курса
COURSE_PREVIEW_TEMPLATE = (
    "<b>🎓 {title}</b>\n\n"
    "<i>Описание</i>}\n"
    "<blockquote>{description}</blockquote>"
)

# Сообщение с превью для модуля
MODULE_PREVIEW_TEMPLATE = (
    "📚 {title}\n\n"
    "<i>О чём этот модуль?</i>\n"
    "<blockquote>{description}</blockquote>}"
)

# Текст сообщения для сгенерированного тестирования
GENERATED_TEST_TEMPLATE = (
    "Тестирование готово!\n\n"
    "🧩 {title}\n\n"
    "❓ Количество вопросов - {questions_count}\n"
    "⏱️ Время выполнения - <u>{estimated_time_minutes}</u>"
)

# Текст для сообщения для вопроса с выбором варианта ответа
MULTIPLE_CHOICE_QUESTION_TEMPLATE = (
    "<b>❓ Вопрос №{number}</b>\n"
    "Пройдено - <u>{passed_percent}%</u>\n\n"
    "{text}\n\n"
    "<b>Варианты ответа:</b>\n"
    "{options}"
)
