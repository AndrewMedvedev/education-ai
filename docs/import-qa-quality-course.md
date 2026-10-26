# Импорт курса QA-инженерии на сервер

Готовый курс находится в `backend/course_data/qa_quality_engineering_m6_m7.json`. Он рассчитан на импорт **напрямую в PostgreSQL через ORM приложения**, без фронтенда и без API-токена.

Импортёр идемпотентен: повторный запуск с тем же JSON безопасно пропустит уже созданный курс. Чтобы осознанно заменить его новой версией, передайте `--replace`.

## 1. Доставьте файлы на сервер

Вместе с обычным деплоем должны попасть три файла:

```text
backend/course_data/qa_quality_engineering_m6_m7.json
backend/scripts/import_course_json.py
docs/import-qa-quality-course.md
```

Проверьте, что backend запущен и миграции применены:

```bash
docker compose ps backend
docker compose exec backend python -c "from src.courses.infra.database.models import CourseOrm; print('ORM OK')"
```

## 2. Узнайте UUID автора курса

Укажите UUID существующего администратора или преподавателя. Команда ниже выводит ID и email пользователей:

```bash
docker compose exec postgres psql -U "$POSTGRES_USERNAME" -d "$POSTGRES_DB" -c 'SELECT id, email FROM users ORDER BY created_at;'
```

Скопируйте UUID нужного пользователя в переменную на сервере:

```bash
CREATOR_ID="вставьте-uuid-пользователя"
```

## 3. Импорт

Запустите из корня репозитория:

```bash
docker compose exec -T backend python scripts/import_course_json.py \
  --course-file course_data/qa_quality_engineering_m6_m7.json \
  --creator-id "$CREATOR_ID"
```

Ожидаемый результат:

```text
IMPORTED: QA-инженерия: качество, риски и Agile-практики (dce0a44e-383d-4955-8f9a-90fba5e4a6f0)
```

Курс сразу публикуется и доступен в каталоге. Его постоянный ID: `dce0a44e-383d-4955-8f9a-90fba5e4a6f0`.

## 4. Проверка после импорта

```bash
docker compose exec postgres psql -U "$POSTGRES_USERNAME" -d "$POSTGRES_DB" -c "
SELECT c.title, c.status, count(DISTINCT m.id) AS modules, count(l.id) AS lessons
FROM courses c
LEFT JOIN modules m ON m.course_id = c.id
LEFT JOIN lessons l ON l.module_id = m.id
WHERE c.id = 'dce0a44e-383d-4955-8f9a-90fba5e4a6f0'
GROUP BY c.id, c.title, c.status;"
```

Ожидаемые значения: `published`, 4 модуля, 8 уроков.

## Обновление курса

`--replace` удаляет и заново создаёт **только** курс с фиксированным ID и все зависимые модули/уроки. Не используйте флаг, если в курсе уже есть важный пользовательский прогресс или ручные правки в интерфейсе.

```bash
docker compose exec -T backend python scripts/import_course_json.py \
  --course-file course_data/qa_quality_engineering_m6_m7.json \
  --creator-id "$CREATOR_ID" --replace
```
