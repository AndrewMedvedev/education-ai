# Courses Backend (MVP)

## Run

```bash
cd backend
.venv\\Scripts\\activate
python -m uvicorn main:app --reload --port 8001
```

## Documentation

- [Permissions](docs/permissions.md) — подробное описание системных прав по модулям, scopes и назначению.
- [API ИИ-агентов Courses](docs/ai-agents-api.md) — HTTP-контракты интервьюера, редактора и ментора, внутренняя генерация курсов и агенты практики.
- [API документов курса](docs/documents-api.md) — загрузка пользовательских документов, конвертация файлов в Markdown, ограничения и ошибки.

## API

- `POST /api/v1/courses`
- `GET /api/v1/courses`
- `GET /api/v1/courses/{course_id}`
- `PATCH /api/v1/courses/{course_id}`
- `DELETE /api/v1/courses/{course_id}` (soft delete)
- CRUD for blocks/lessons/practice
- enrollment/progress endpoints
- practice attempts endpoints
- async course generation endpoints
- document upload and Markdown conversion endpoints

## OpenAI-compatible generation

Generation uses LangChain/LangGraph through OpenAI-compatible API.

For Yandex AI Studio compatible mode, set:

- `OPENAI_API_KEY=<yandex_api_key>`
- `OPENAI_BASE_URL=https://llm.api.cloud.yandex.net/v1`
- `YANDEX_FOLDER_ID=<folder_id>`

Swagger: `http://localhost:8001/docs`
