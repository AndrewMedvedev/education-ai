# Модуль `core`

## 1. Название и краткое описание

`core` содержит инфраструктурное ядро приложения: создание FastAPI app, lifespan, настройки, БД, Redis, Rabbit, S3, Qdrant, monitoring, logging и Dramatiq. Это не бизнес-модуль, а shared infrastructure layer для остальных модулей.

## 2. Границы ответственности

**Делает:** конфигурирует приложение и внешние подключения. **Не делает:** не содержит бизнес-сущности, публичный domain API и REST endpoints модулей, кроме monitoring.

## 3. Глоссарий

| Термин | Значение |
|---|---|
| `app` | FastAPI instance из `fastapi.py`. |
| `lifespan` | Startup/shutdown lifecycle. |
| `broker` | Rabbit/FastStream broker. |
| `session_factory` | SQLAlchemy async session factory. |

## 4. Структура папок

```text
backend/src/core/
├── database/       # SQLAlchemy base/config/connection
├── mail/           # mail config
├── monitoring/     # health/prometheus
├── providers/      # provider configs
├── qdrant/         # qdrant client/config
├── rabbit/         # RabbitRouter/broker/exchange
├── redis/          # redis client/config
├── retrieval/      # retrieval config/rest
├── s3/             # S3 config
├── dramatiq.py     # Dramatiq setup
├── fastapi.py      # FastAPI app/middleware/prometheus
├── lifespan.py     # startup tasks
├── logging.py      # logging setup
└── settings.py     # app settings
```

## 5. Доменная модель

Не применимо: доменной модели нет.

## 6. Ключевые сценарии (use cases)

| Сценарий | Входные данные | Шаги | Результат | Ошибки |
|---|---|---|---|---|
| Startup | FastAPI lifecycle | logging → Redis ping → bootstrap CLI → checkpointer setup → Qdrant collection ensure | приложение готово | Redis/Qdrant/bootstrap errors |
| Health check | GET `/health` | return dict | `{status: ok}` | unhandled |
| Prometheus | app setup | instrumentator expose `/metrics` | metrics endpoint | unhandled |

## 7. Публичный API модуля

| Метод | Путь | Назначение | Авторизация | Файл |
|---|---|---|---|---|
| GET | `/health` | Health check, `include_in_schema=False` | Нет | `monitoring/health.py` |
| GET | `/metrics` | Prometheus metrics, `include_in_schema=False` | Нет | `monitoring/prometheus.py` |

### GET `/health`

Ответ `200 OK`:

```json
{"status":"ok"}
```

Ошибки не заданы явно; возможен 500 при runtime failure. Идемпотентен, побочных эффектов нет.

## 8. События

`core/rabbit/__init__.py` создаёт `RabbitRouter`, `broker` и `events_exchange`; сам core business events не публикует.

## 9. Хранение данных

Собственных таблиц нет. `database/base.py`, `connection.py`, `config.py` используются всеми ORM-модулями.

## 10. Зависимости

FastAPI, CORSMiddleware, Prometheus instrumentator, Redis, Rabbit/FastStream, Qdrant, SQLAlchemy, S3, Dramatiq.

## 11. Конфигурация

| Параметр | Назначение | Значение по умолчанию | Обязательность |
|---|---|---|---|
| `app_config.version` | Версия API | settings | Для app metadata |
| DB config | PostgreSQL connection | `database/config.py` | Обязательно для БД |
| Redis config | Redis/checkpointer/blacklist | `redis/config.py` | Обязательно для startup по коду ping |
| Rabbit config | broker/exchange | `rabbit/config.py` | Для events |
| Qdrant config | vector collection | `qdrant/config.py` | Startup проверяет `MAIN_COLLECTION` |
| S3 config | object storage | `s3/config.py` | Для media |

## 12. Фоновые процессы

Dramatiq настраивается в `dramatiq.py`. Конкретные actors находятся в бизнес-модулях, например `courses/agents/course_generator/workflow.py`.

## 13. Безопасность и права доступа

Core не реализует auth. CORS middleware конфигурируется в `fastapi.py`. `/health` и `/metrics` не имеют auth по коду.

## 14. Каталог ошибок модуля и их HTTP-статусов

### a) Единый формат ошибки

Core подключается к app до `setup_exception_handlers(app)` в `main.py`, но сам handler живёт в `shared/api/exception_handler.py`.

### b) Таблица ошибок

| Ошибка | HTTP | Когда | Где |
|---|---:|---|---|
| Startup Redis/Qdrant error | не HTTP / startup fail | `lifespan` | `lifespan.py` |
| Unhandled | 500 | health/metrics runtime error | monitoring |

### c) Правила маппинга

Для HTTP применяется FastAPI/shared handlers, если app стартовал.

### d) Формат ошибок валидации

Не применимо для `/health`.

## 15. Тестирование

Тесты core не найдены.

## 16. Как с этим работать разработчику

Добавляйте инфраструктурные clients/config здесь, но не бизнес-логику. Startup actions должны быть безопасны при повторном запуске.

## 17. Наблюдения и технический долг

- `lifespan` делает Redis ping и Qdrant collection creation на startup; при недоступности сервисов приложение не стартует.
- `/metrics` и `/health` публичны.

## 18. Открытые вопросы

- Нужно ли защищать `/metrics`?
- Должны ли bootstrap CLI команды запускаться в каждом startup окружении?
