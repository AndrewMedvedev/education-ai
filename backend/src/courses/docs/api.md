# API модуля `courses`

Глобальный префикс роутера задаётся в `backend/src/__init__.py`: `/api/v1`. Все пути ниже указаны с этим префиксом.

## Общие DTO

| DTO | Файл | Поля |
|---|---|---|
| `CourseSchema` | `application/dtos.py` | `title: str`, `description: str`, `difficulty: DifficultyLevel`, `tags: list[str]` |
| `EditCourseSchema` | `application/dtos.py` | nullable `title`, `description`, `difficulty`, `tags` |
| `ModuleSchema` | `application/dtos.py` | `title`, `description`, `order`, `learning_objectives` |
| `EditModuleSchema` | `application/dtos.py` | nullable `title`, `description`, `order`, `learning_objectives` |
| `LessonSchema` | `application/dtos.py` | `title`, `description`, `order`, `learning_objectives`, `estimated_time_minutes` |
| `EditLessonSchema` | `application/dtos.py` | nullable поля урока |
| `Chat` | `application/dtos.py` | `chat_id`, `course_id`, `role`, `content` |
| `EditorChat` | `application/dtos.py` | `Chat` + `content_type`, `content_block`, `content_blocks`, `images` |
| `MentorChat` | `application/dtos.py` | `Chat` + `content_blocks` |
| `InvitationCreate` | `application/dtos.py` | `course_id`, `email`, `role` |
| `LessonTheorySessionEditSchema` | `application/dtos.py` | `completed_at`, `active_time_seconds`, `max_scroll_depth_percent` |
| `Pagination` | `shared/application/dtos.py` | `page`, `size` |

## Общие ошибки

| HTTP-статус | Код/тип ошибки | Когда возникает | Пример тела ответа |
|---:|---|---|---|
| 400 | `VALIDATION_ERROR` / `ValueError` | Ошибки value object/helper validation | `{"error":{"grant":"VALIDATION_ERROR","message":"...","status":400,"details":{}}}` |
| 401 | `UNAUTHORIZED` | Нет/невалидный Bearer token | `{"error":{"code":"UNAUTHORIZED","message":"...","details":{}}}` |
| 403 | `PERMISSION_DENIED` | Не хватает permission/policy | `{"error":{"code":"PERMISSION_DENIED","message":"...","details":{}}}` |
| 404 | `RESOURCE_NOT_FOUND` | Не найдена сущность | `{"error":{"code":"RESOURCE_NOT_FOUND","message":"...","details":{}}}` |
| 409 | `ALREADY_EXISTS`/`INVARIANT_VIOLATION` | Дубликаты или бизнес-инварианты | `{"error":{"code":"ALREADY_EXISTS","message":"...","details":{}}}` |
| 413 | `PAYLOAD_TOO_LARGE` | Превышен лимит файла | `{"error":{"code":"PAYLOAD_TOO_LARGE","message":"...","details":{}}}` |
| 422 | FastAPI/Pydantic validation | Невалидный body/query/path | `{"detail":[...]}` |
| 500 | Unhandled exception | Ошибка без маппинга | Стандартный ответ FastAPI/ASGI |

## Обзор endpoints

| Метод | Путь | Назначение | Авторизация | Файл |
|---|---|---|---|---|
| POST | `/api/v1/course/create` | Создать курс | permission `course:create` | `api/v1/course.py` |
| POST | `/api/v1/course/` | Список курсов | не задана | `api/v1/course.py` |
| POST | `/api/v1/course/my-courses` | Мои курсы | Bearer | `api/v1/course.py` |
| GET | `/api/v1/course/{course_id}/status` | Статус курса | Bearer | `api/v1/course.py` |
| GET | `/api/v1/course/basic/info/{course_id}` | Basic info курса | не задана | `api/v1/course.py` |
| PUT | `/api/v1/course/edit/{course_id}` | Редактировать курс | course `UPDATE` | `api/v1/course.py` |
| POST | `/api/v1/course/publish/{course_id}` | Опубликовать курс | course `UPDATE` | `api/v1/course.py` |
| DELETE | `/api/v1/course/delete/{course_id}` | Архивировать курс | course `DELETE` | `api/v1/course.py` |
| POST | `/api/v1/course/{course_id}/invite-only` | Invite-only курс | course `UPDATE` | `api/v1/course.py` |
| POST | `/api/v1/module/create` | Создать модуль | permission `course:create` | `api/v1/module.py` |
| POST | `/api/v1/module/assign/{module_id}/{course_id}` | Привязать модуль | course `UPDATE` | `api/v1/module.py` |
| GET | `/api/v1/module/basic/info/{module_id}` | Basic info модуля | course `READ` | `api/v1/module.py` |
| PUT | `/api/v1/module/edit/{module_id}` | Редактировать модуль | course `UPDATE` | `api/v1/module.py` |
| DELETE | `/api/v1/module/{module_id}` | Удалить модуль | permission/delete access | `api/v1/module.py` |
| POST | `/api/v1/lesson/create` | Создать урок | не задана | `api/v1/lesson.py` |
| POST | `/api/v1/lesson/assign/{lesson_id}/{module_id}` | Привязать урок | course `UPDATE` | `api/v1/lesson.py` |
| GET | `/api/v1/lesson/basic/info/{lesson_id}` | Basic info урока | course `READ` | `api/v1/lesson.py` |
| GET | `/api/v1/lesson/theory/{lesson_id}` | Теория урока | course `READ` | `api/v1/lesson.py` |
| PUT | `/api/v1/lesson/edit/{lesson_id}` | Редактировать урок | course `UPDATE` | `api/v1/lesson.py` |
| PUT | `/api/v1/lesson/update/{lesson_id}` | Обновить blocks | course `UPDATE` | `api/v1/lesson.py` |
| DELETE | `/api/v1/lesson/{lesson_id}` | Удалить урок | course `DELETE` | `api/v1/lesson.py` |
| POST | `/api/v1/members/{course_id}/sign` | Записаться | Bearer | `api/v1/member.py` |
| POST | `/api/v1/members/` | Курсы участника | Bearer | `api/v1/member.py` |
| POST | `/api/v1/members/{course_id}` | Студенты курса | permission `course:update` | `api/v1/member.py` |
| POST | `/api/v1/agent/interviewer` | Чат интервьюера | Bearer | `api/v1/agents.py` |
| POST | `/api/v1/agent/editor` | Чат редактора | course `UPDATE` | `api/v1/agents.py` |
| POST | `/api/v1/agent/mentor` | Чат ментора | course `READ` | `api/v1/agents.py` |
| POST | `/api/v1/agent/test/{module_id}/{lesson_id}` | Создать тест | course `READ` via module | `api/v1/agents.py` |
| POST | `/api/v1/agent/check/test/{practice_id}` | Проверить тест | Bearer | `api/v1/agents.py` |
| POST | `/api/v1/agent/practice/{module_id}/{lesson_id}` | Создать практику | course `READ` via module | `api/v1/agents.py` |
| POST | `/api/v1/agent/check/practice/{practice_id}` | Проверить практику | Bearer | `api/v1/agents.py` |
| POST | `/api/v1/documents/to/markdown` | Конвертировать документ | Bearer | `api/v1/documents.py` |
| POST | `/api/v1/documents/upload` | Загрузить документ | Bearer | `api/v1/documents.py` |
| POST | `/api/v1/courses/invitations` | Создать приглашение | invite policy | `api/v1/invitations.py` |
| POST | `/api/v1/courses/invitations/accept/{token}` | Принять приглашение | Bearer | `api/v1/invitations.py` |
| POST | `/api/v1/theory/session/{lesson_id}` | Создать theory session | course `READ` | `api/v1/theory_session.py` |
| PUT | `/api/v1/theory/session/{theory_session_id}` | Обновить metrics | Bearer | `api/v1/theory_session.py` |
| GET | `/api/v1/theory/session/{lesson_id}/{user_id}` | Получить sessions | permission theory `READ` | `api/v1/theory_session.py` |

## Детализация endpoints

### POST `/api/v1/course/create`

**Назначение:** создаёт курс.

**Авторизация:** `Depends(require_permissions(CREATE.code))`, permission из `domain/permissions/courses.py`.

**Запрос:** body `CourseSchema`.

| Поле | Тип | Обяз. | Ограничения | Описание |
|---|---|---:|---|---|
| `title` | `str` | да | Pydantic string | Название курса |
| `description` | `str` | да | Pydantic string | Описание |
| `difficulty` | `DifficultyLevel` | да | `beginner/intermediate/advanced/expert` | Сложность |
| `tags` | `list[str]` | да | list | Теги |

Пример:

```json
{"title":"Python basics","description":"Intro","difficulty":"beginner","tags":["python"]}
```

**Успешный ответ:** `201 Created`, тело `Course` domain entity.

**Ошибки:** общие 401/403/422/500; бизнес-ошибки сервиса как `DomainError`.

**Побочные эффекты:** запись в `courses`, commit в session. **Идемпотентность:** неидемпотентен.

### POST `/api/v1/course/`

**Назначение:** возвращает страницу курсов.

**Авторизация:** не задана в decorator/signature.

**Запрос:** body `Pagination` (`page: PositiveInt`, `size: PositiveInt`).

**Успешный ответ:** `200 OK`, `Page[Course]`.

**Ошибки:** 422 validation, 500; auth errors не следуют из кода endpoint.

**Побочные эффекты:** нет. **Идемпотентность:** идемпотентен как read operation.

### POST `/api/v1/course/my-courses`

**Назначение:** возвращает курсы текущего пользователя.

**Авторизация:** `CurrentIdentity`.

**Запрос:** body `Pagination`.

**Успешный ответ:** `200 OK`, `Page[Course]`.

**Ошибки:** 401, 422, 500.

**Побочные эффекты:** нет. **Идемпотентность:** идемпотентен.

### GET `/api/v1/course/{course_id}/status`

**Route-параметры:** `course_id: UUID`.

**Авторизация:** `CurrentIdentity`.

**Успешный ответ:** `200 OK`.

```json
{"status":"draft"}
```

**Ошибки:** `404 HTTPException` если repository вернул `None`; 401; 422; 500.

**Побочные эффекты:** нет. **Идемпотентность:** идемпотентен.

### GET `/api/v1/course/basic/info/{course_id}`

**Route-параметры:** `course_id: UUID`.

**Авторизация:** не задана.

**Успешный ответ:** `200 OK`, `CourseBasicInfo` из `domain/entities.py`.

**Ошибки:** `NotFoundError` 404 из `BaseCourseService.get_basic_info`; 422; 500.

**Побочные эффекты:** нет. **Идемпотентность:** идемпотентен.

### PUT `/api/v1/course/edit/{course_id}`

**Route-параметры:** `course_id: UUID`. **Body:** `EditCourseSchema` с nullable полями.

**Авторизация:** `CurrentIdentity` + `CheckAccessDep` для `UPDATE`.

**Успешный ответ:** `200 OK`, `Course`.

**Ошибки:** 401/403/404/422/500.

**Побочные эффекты:** update `courses`. **Идемпотентность:** идемпотентен при одинаковом body.

### POST `/api/v1/course/publish/{course_id}`

**Route-параметры:** `course_id: UUID`. **Body:** нет.

**Авторизация:** `CurrentIdentity` + `CheckAccessDep(UPDATE)`.

**Успешный ответ:** `200 OK`, тело `null`.

**Побочные эффекты:** статус курса становится `published`. **Идемпотентность:** зависит от сервиса; явной защиты/ключа идемпотентности нет.

### DELETE `/api/v1/course/delete/{course_id}`

**Route-параметры:** `course_id: UUID`.

**Авторизация:** `CurrentIdentity` + `CheckAccessDep(DELETE)`.

**Успешный ответ:** `200 OK`, тело `null`. В коде endpoint вызывает `service.delete(course_id)`, по анализу сервиса операция архивирует курс.

**Ошибки:** 401/403/404/422/500.

**Побочные эффекты:** update `courses.status = archived`. **Идемпотентность:** не подтверждена кодом.

### POST `/api/v1/course/{course_id}/invite-only`

Аналогичен publish, но переводит статус курса в `invite_only`. Авторизация `UPDATE`, успешный ответ `200 OK`, тело `null`.

### POST `/api/v1/module/create`

**Запрос:** query `course_id: UUID | None`; body `ModuleSchema`.

**Авторизация:** `require_permissions(CREATE.code)`.

**Успешный ответ:** `201 Created`, `Module`.

**Ошибки:** 401/403/404 при несуществующем course_id, 422, 500.

**Побочные эффекты:** insert `modules`; возможно связь с `courses`. **Идемпотентность:** неидемпотентен.

### POST `/api/v1/module/assign/{module_id}/{course_id}`

**Route:** `module_id: UUID`, `course_id: UUID`.

**Авторизация:** `CheckAccessDep(UPDATE)`.

**Успешный ответ:** `200 OK`, `null`.

**Ошибки:** 401/403/404/422/500.

**Побочные эффекты:** обновляет `modules.course_id`. **Идемпотентность:** при той же привязке фактически идемпотентен, но явно не оформлено.

### GET `/api/v1/module/basic/info/{module_id}`

**Route:** `module_id: UUID`. **Авторизация:** `CheckAccessDep(READ)`.

**Успешный ответ:** `200 OK`, `ModuleBasicInfo`.

**Ошибки:** 401/403/404/422/500. **Побочные эффекты:** нет. **Идемпотентность:** да.

### PUT `/api/v1/module/edit/{module_id}`

**Route:** `module_id`. **Body:** `EditModuleSchema`. **Авторизация:** `CheckAccessDep(UPDATE)`.

**Успешный ответ:** `200 OK`, `Module`. **Ошибки:** 401/403/404/422/500. **Побочные эффекты:** update `modules`.

### DELETE `/api/v1/module/{module_id}`

**Авторизация:** `require_permissions(DELETE.code)` + `CheckAccessDep(DELETE)`.

**Успешный ответ:** `204 No Content`. **Ошибки:** 401/403/404/422/500. **Побочные эффекты:** delete module через service/repository.

### POST `/api/v1/lesson/create`

**Запрос:** query `module_id: UUID | None`; body `LessonSchema`.

**Авторизация:** не задана.

**Успешный ответ:** `201 Created`, `Lesson`.

**Ошибки:** 404 при несуществующем module_id из сервиса, 422, 500.

**Побочные эффекты:** insert `lessons`. **Идемпотентность:** неидемпотентен.

### POST `/api/v1/lesson/assign/{lesson_id}/{module_id}`

**Route:** `lesson_id`, `module_id`. **Авторизация:** `CheckAccessDep(UPDATE)`.

**Ответ:** `200 OK`, `null`. **Ошибки:** 401/403/404/422/500. **Побочные эффекты:** update `lessons.module_id`.

### GET `/api/v1/lesson/basic/info/{lesson_id}`

**Route:** `lesson_id`. **Авторизация:** `CheckAccessDep(READ)`. **Ответ:** `200 OK`, `LessonBasicInfo`. **Ошибки:** 401/403/404/422/500.

### GET `/api/v1/lesson/theory/{lesson_id}`

**Route:** `lesson_id`. **Авторизация:** `CheckAccessDep(READ)`.

**Ответ:** `200 OK`, `list[AnyContentBlock]`. Пример зависит от concrete union item, например text block:

```json
[{"content_type":"text","ai_generated":true,"md_content":"# Theory"}]
```

**Ошибки:** 401/403/404/422/500.

### PUT `/api/v1/lesson/edit/{lesson_id}`

**Body:** `EditLessonSchema`. **Авторизация:** `CheckAccessDep(UPDATE)`. **Ответ:** `200 OK`, `Lesson`. **Ошибки:** 401/403/404/422/500.

### PUT `/api/v1/lesson/update/{lesson_id}`

**Body:** `list[AnyContentBlock]` из `domain/vo.py`.

**Авторизация:** `CheckAccessDep(UPDATE)`. **Ответ:** `200 OK`, `Lesson`. **Ошибки:** 401/403/404/422/500. **Побочные эффекты:** перезапись `lessons.content_blocks`.

### DELETE `/api/v1/lesson/{lesson_id}`

**Авторизация:** `CheckAccessDep(DELETE)`. **Ответ:** `204 No Content`. **Ошибки:** 401/403/404/422/500.

### POST `/api/v1/members/{course_id}/sign`

**Route:** `course_id`. **Авторизация:** `CurrentIdentity`.

**Ответ:** `201 Created`, `Member`. **Ошибки:** 401/404/409/422/500. **Побочные эффекты:** insert `members`. **Идемпотентность:** неидемпотентен; повтор может дать conflict.

### POST `/api/v1/members/`

**Body:** `Pagination`. **Авторизация:** `CurrentIdentity`.

**Ответ:** `200 OK`, `Page[Course]`. **Побочные эффекты:** нет. **Ошибки:** 401/422/500.

### POST `/api/v1/members/{course_id}`

**Route:** `course_id`; body `Pagination`.

**Авторизация:** `require_permissions(UPDATE.code)`. **Ответ:** `200 OK`, `Page[Member]`. **Ошибки:** 401/403/404/422/500.

### POST `/api/v1/agent/interviewer`

**Body:** `Chat`. **Авторизация:** `CurrentIdentity`.

**Ответ:** `200 OK`, `Chat` с ролью assistant/content от агента. **Ошибки:** 401/422/500; ошибки LLM без явного маппинга могут стать 500.

### POST `/api/v1/agent/editor`

**Body:** `EditorChat`. **Авторизация:** `CurrentIdentity` + access `UPDATE` по `course_id`.

**Ответ:** `200 OK`, `Chat`, где content содержит JSON-строку результата редактора. **Ошибки:** 401/403/404/422/500.

### POST `/api/v1/agent/mentor`

**Body:** `MentorChat`. **Авторизация:** `CurrentIdentity` + access `READ`.

**Ответ:** `200 OK`, `Chat`. **Ошибки:** 401/403/404/422/500.

### POST `/api/v1/agent/test/{module_id}/{lesson_id}`

**Route:** `module_id`, `lesson_id`. **Авторизация:** `CurrentIdentity` + access `READ` через module.

**Ответ:** `201 Created`, `dict[str, Any]` с тестом из agent schema (`AnyKnowledgeTest`). **Ошибки:** 401/403/404/422/500. **Побочные эффекты:** создаётся/сохраняется практика через agent/repository по коду агента. **Идемпотентность:** не подтверждена.

### POST `/api/v1/agent/check/test/{practice_id}`

**Route:** `practice_id`. **Body:** объект с `practice: AnyKnowledgeTest`, `answers: dict[str,str]`.

**Авторизация:** `CurrentIdentity`.

**Ответ:** `200 OK`, `PracticeResult`:

```json
{"score":80.0,"ai_feedback":"..."}
```

**Ошибки:** 401/404/422/500. Проверка доступа к `practice_id` в endpoint не видна.

### POST `/api/v1/agent/practice/{module_id}/{lesson_id}`

**Route:** `module_id`, `lesson_id`. **Авторизация:** `CurrentIdentity` + access `READ` через module.

**Ответ:** `201 Created`, assignment payload (`FileUploadAssignment` или `GitHubAssignment`). **Ошибки:** 401/403/404/422/500.

### POST `/api/v1/agent/check/practice/{practice_id}`

**Route:** `practice_id`. **Запрос:** multipart `file: UploadFile`, form `practice` JSON как `FileUploadAssignment`.

**Авторизация:** `CurrentIdentity`.

**Ответ:** `200 OK`, `PracticeResult`. **Ошибки:** 401/404/422/500.

### POST `/api/v1/documents/to/markdown`

**Запрос:** multipart `file`. Поддержанные расширения в `api/v1/documents.py`: `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.md`, `.html`, `.txt`, `.json`.

**Авторизация:** `CurrentIdentity`.

**Ответ:** `200 OK`, строка markdown.

**Ошибки:**

| Статус | Тип | Когда |
|---:|---|---|
| 400 | `HTTPException` | Расширение не разрешено или файл пустой |
| 413 | `PayloadTooLargeError` | Превышен лимит чтения |
| 401 | `UNAUTHORIZED` | Нет Bearer token |
| 422 | FastAPI | Нет multipart file |

**Побочные эффекты:** временная обработка файла; БД не пишется. **Идемпотентность:** да для одинакового файла.

### POST `/api/v1/documents/upload`

**Запрос:** multipart `file`, те же расширения.

**Авторизация:** `CurrentIdentity`.

**Ответ:** `201 Created`:

```json
{"message":"Файл загружен"}
```

**Ошибки:** как у `/documents/to/markdown`. **Побочные эффекты:** `DocumentServiceDep`/pipeline сохраняет документ/узлы по реализации сервиса. **Идемпотентность:** не подтверждена.

### POST `/api/v1/courses/invitations`

**Body:** `InvitationCreate` (`course_id`, `email`, `role`).

**Авторизация:** policy invite из `domain/permissions/invitations.py`.

**Ответ:** `201 Created`, `Invitation`.

**Ошибки:** 401/403/404/409/422/500. **Побочные эффекты:** insert `course_invitations`, событие `CourseInvited`.

### POST `/api/v1/courses/invitations/accept/{token}`

**Route:** `token: str`. **Авторизация:** `CurrentIdentity`.

**Ответ:** `201 Created`, `Member`. **Ошибки:** 401/404/409/422/500. **Побочные эффекты:** создаёт `Member`, помечает приглашение использованным по сервисной логике.

### POST `/api/v1/theory/session/{lesson_id}`

**Route:** `lesson_id`. **Авторизация:** `CurrentIdentity` + course `READ` through lesson.

**Ответ:** `201 Created`, `LessonTheorySession`. **Ошибки:** 401/403/404/422/500. **Побочные эффекты:** insert `lesson_theory_sessions`. **Идемпотентность:** неидемпотентен.

### PUT `/api/v1/theory/session/{theory_session_id}`

**Route:** `theory_session_id`. **Body:** `LessonTheorySessionEditSchema`.

**Авторизация:** `CurrentIdentity`.

**Ответ:** `200 OK`, `LessonTheorySession`.

**Ошибки:** `404 HTTPException` с `detail: "Metrics not found"`, 401, 422, 500. Проверка владельца session в endpoint не видна.

### GET `/api/v1/theory/session/{lesson_id}/{user_id}`

**Route:** `lesson_id`, `user_id`. **Query:** `LessonTheorySessionFilters` + базовые filter params.

**Авторизация:** `require_permissions(theory_session.READ.code)` + `CheckAccessDep(READ)`.

**Ответ:** `200 OK`, `list[LessonTheorySession]`.

**Ошибки:** 401/403/404/422/500. **Побочные эффекты:** нет. **Идемпотентность:** да.
