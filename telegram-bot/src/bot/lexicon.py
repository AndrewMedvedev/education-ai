
CONFETTI_EFFECT_ID = "5104841245755180586"
FAIL_EFFECT_ID = "5104858069142078462"
FIRE_EFFECT_ID = "5107584321108051014"

# Командное меню студента
STUDENT_CMD_MENU_TEXT = (
    "<b>⚙️ Главное меню</b>\n\n"
    " - /study - <i>🎓 изучение курса</i>\n"
    " - /profile - <i>👤 мой профиль</i>\n"
    " - /leaderboard - <i>🏆 доска лидеров</i>\n"
    " - /info - <i>ℹ️ информация о боте, инструкции</i>\n"
    " - /support - <i>🛠️ баг-репорты и обратная связь</i>"
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
    "<blockquote>{description}</blockquote>\n\n"
    "1. Изучите теорию\n"
    "2. Пройдите тестирование\n"
    "3. Если вы набрали <u>61</u> и более баллов за тест, то вам откроется практическое задание"
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

# Текст сообщения для вопроса с развёрнутым ответом
DETAILED_ANSWER_QUESTION_TEMPLATE = (
    "<b>❓ Вопрос №{number}</b>\n"
    "Пройдено - <u>{passed_percent}%</u>\n\n"
    "{text}\n\n"
    "💡 Подсказка:\n"
    "<tg-spoiler>{hint}</tg-spoiler>\n\n"
    "<i>Дайте развёрнутый ответ:</i>"
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
    "✅ Правильных ответов: <u>{correct_answers_count}</u>"
)

GOOD_TEST_RESULT_TEMPLATE = (
    "🏅 Вы набрали более 80 баллов!\n\n"
    "💪 Набрано баллов: {score}\n"
    "✅ Правильных ответов: <u>{correct_answers_count}</u>"
)

GREAT_TEST_RESULT_TEMPLATE = (
    "🏆 Вы набрали <b>максимальное</b> количество баллов!\n\n"
    "💯 Набрано баллов: {score}\n"
    "✅ Правильных ответов: <u>{correct_answers_count}</u>"
)

# Шаблон сообщения для профиля студента
STUDENT_PROFILE_TEMPLATE = (
    "<b>👤 Профиль студента {user_mention}:</b>\n\n"
    "<b>ℹ️ Общая информация:</b>\n"
    " - ФИО: <u>{full_name}</u>\n"
    " - Группа: <u>{group}</u>\n\n"
    "<b>🎓 Учебный прогресс:</b>\n"
    " - Количество баллов: <u>{total_score}</u>\n"
    " - Пройдено уроков: <u>{learning_percent}%</u>"
)

AI_FEEDBACK_TEMPLATE = (
    "<b>💬 Обратная связь:</b>\n\n"
    "{ai_feedback}"
)

# Сообщение при истёкшей сессии
SESSION_EXPIRED_TEXT = (
    "⌛ Похоже, что ваша сессия истекла ...\n\n"
    "<i>Для продолжения обучения нажмите 👇</i>\n"
    "/study"
)

# Шаблон сообщения для задания с загрузкой файла
FILE_UPLOAD_ASSIGNMENT_TEMPLATE = (
    "<b>🔗 Задание с загрузкой файла</b>\n\n"
    "<u>📌 Постановка задачи:</u>\n"
    "{description}\n\n"
    "<u>⚙️ Инструкция по оформлению:</u>\n"
    "<blockquote expandable>{submission_instructions}</blockquote>\n\n"
    "<u>📂 Разрешённые форматы файлов:</u>\n"
    "{allowed_extensions}\n\n"
    "<b>Статус:</b> <i>{status_msg}</i>"
)

# Шаблон сообщения с результатом практического задания
ASSIGNMENT_RESULT_TEMPLATE = (
    "<b>✔️ Задание проверено</b>\n\n"
    "📊 Набрано баллов: <u>{score}</u>\n\n"
    "<i>💭 Обратная связь</i>\n"
    "{ai_feedback}"
)
