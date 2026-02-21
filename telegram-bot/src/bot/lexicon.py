from aiogram.utils.formatting import Bold, BotCommand, Text, as_line, as_marked_section

# Эффект сообщения с конфетти
CONFETTI_EFFECT_ID = "5104841245755180586"
FAIL_EFFECT_ID = "5104858069142078462"
FIRE_EFFECT_ID = "5107584321108051014"

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
    "<i>Описание</i>\n"
    "<blockquote>{description}</blockquote>"
)

# Сообщение с превью для модуля
MODULE_PREVIEW_TEMPLATE = (
    "<b>📚 {title}</b>\n\n"
    "<i>О чём этот модуль?</i>\n"
    "<blockquote>{description}</blockquote>"
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


# Шаблоны сообщений с результатами тестирования
FAILED_TEST_RESULT_TEMPLATE = (
    "😞 К сожалению, вы не прошли тестирование ...\n\n"
    "🚨 Набрано баллов: <b>{score}</b>\n"
    "✅ Правильных ответов: <u>{correct_answers_count}</u>"
)

PASSED_TEST_RESULT_TEMPLATE = (
    "🔝 Тестирование пройдено!\n\n"
    "👍 Набрано баллов: <b>{score}</b>\n"
    "✅ Правильных ответов: <u>{correct_answers_count}"
)

GOOD_TEST_RESULT_TEMPLATE = (
    "🏅 Вы набрали более 80 баллов!\n\n"
    "💪 Набрано баллов: {score}\n"
    "✅ Правильных ответов: <u>{correct_answers_count}"
)

GREAT_TEST_RESULT_TEMPLATE = (
    "🏆 Вы набрали <b>максимальное</b> количество баллов!\n\n"
    "💯 Набрано баллов: {score}\n"
    "✅ Правильных ответов: <u>{correct_answers_count}"
)
