# Инструкции для Backend

Применяются вместе с корневым `AGENTS.md`. Пути ниже — относительно `backend/`;
`src/<module>/...` и пути с `*` — шаблоны, не буквальные имена.

## Тестирование и команды проверок

- Команды — из `backend/`, Python 3.14+. До pytest проверь imports/conftest: даже `--collect-only`
  и `python -m pytest tests/unit/feedback -q` исполняют `src/__init__.py`/settings/чужие imports
  до HTTP overrides. Нужны зависимости и конфигурация; unit/mocks не гарантируют изоляцию collection.
- Pytest/pytest-asyncio, `AsyncMock`, fixtures/overrides. Для поведения — regression test;
  async-правки проверяй на ошибку/отмену, cleanup, bounded concurrency и повтор/resume.
  API-правки — DTO/errors/status и потребители SPA. Если окружения нет, укажи непроверенное,
  не запускай рабочие сервисы вместо изолированных тестов.
- `tests/integration/conftest.py`: Testcontainers PostgreSQL/Redis, create_all/drop_all/flushdb.
  Требуются разрешённый Docker и изоляция. Feedback DB opt-in (`tests/integration/test_feedback_database.py`,
  `RUN_FEEDBACK_DB_TESTS=1`) использует настроенную локальную БД: выдели отдельную с контролируемыми
  данными. Monitoring tests работают с реальными endpoints/очередями/Qdrant; проверь TEST-настройки.
- Часть IAM/LLM/monitoring tests устарела: отделяй исходные падения от регрессий,
  не восстанавливай старый API ради них. Полный suite/seed/LLM не заменяют целевые проверки.
- `src/core/lifespan.py`: вне worker startup делает миграции/CLI bootstrap, checkpointer setup
  и условное создание Qdrant collection. Полный lifespan/TestClient не безопасный smoke-check.
- `pyproject.toml`: Ruff, basedpyright basic, Vulture настроены, но executables не объявлены
  прямыми зависимостями. Если установлены: `ruff check <paths>`, `ruff format --check <paths>`,
  `basedpyright`. Ruff exclusions действуют при обходе; явно переданный файл проверяется,
  если не включён force-exclude. Pytest markers/fixtures смотри в тестах, TOML pytest-секции нет.
- Не запускай `uv run` без оценки sync/install; не устанавливай зависимости вопреки задаче.
  Разделяй статическую проверку, тесты и внешние smoke-checks; сборка/чтение кода не тесты поведения.

## Стек и карта кода

- Python `>=3.14`, окружение `.venv`, зависимости в `pyproject.toml` и `uv.lock`, менеджер uv.
- FastAPI, Pydantic v2/settings; SQLAlchemy 2 async + asyncpg, PostgreSQL, Alembic.
- Redis — кеши/JWT blacklist/checkpoints/cancellation; RabbitMQ — FastStream events и Taskiq;
  Qdrant — hybrid retrieval; RustFS/S3 — файлы. Клиенты: aiohttp, aiobotocore, aiosmtplib.
- OpenAI SDK, LangGraph, собственные LLM services/router; Playwright и конвертация документов.
- `main.py` собирает приложение, `src/__init__.py` — маршруты `/api/v1`.
- `src/core/` — settings, подключения, FastAPI/lifespan, логирование, monitoring, пакет `tkq/`.
- `src/shared/` — entities/errors/events, DTO/Protocol, Transaction, общие адаптеры и helpers.
- `src/iam/` — users/memberships/permissions/JWT/M2M; `src/organization/` — организации/приглашения.
- `src/courses/` — курсы, участники, документы, прогресс, theory sessions, практика и AI.
- `src/media/` — uploads/S3; `src/notifications/` — SMTP/SSE; `src/feedback/` — отзывы;
  `src/activity/` — audit recorder и mapper registry событий.
- `src/llm_service/` — model/tool loop и middleware; `src/llm_router/` — провайдеры/учёт вызовов.
- `src/cli/` — admin-команды; `src/features/` — seed/import/debug с записями и LLM, не unit tests.
- `migrations/`, `tests/`, `templates/` — миграции, тесты, шаблоны писем.

## Фактическая архитектура и границы слоёв

Модульный Backend с DDD-элементами, не строгая Clean/Hexagonal Architecture:
application местами зависит от `AsyncSession`, domain — от settings; есть межмодульные HTTP/импорты.

- Внутри `src/<module>/` (шаблон): API → dependencies → application/services → repository → infra.
  Следуй конкретному модулю. Координация — в service; простые read-endpoints уже обращаются к repo.
- Domain хранит состояние/инварианты; не добавляй туда FastAPI, SQL session или сетевые вызовы.
  `src/shared/` — общие контракты, не бизнес-правила курса/IAM.
- Не вводи CQRS bus, новые handlers/UoW-обёртки без основания в задаче; общего CQRS bus нет.
- HTTP adapters — по шаблонам `src/<module>/infra/external_apis.py` и `src/<module>/infra/services/`.
  Не заменяй их прямым SQL/импортом сервиса без проверки auth и сетевого контракта.

## Domain, DTO и прикладная логика

- Dataclass-сущности часто `kw_only=True, slots=True`; база с UUID/timestamps/events —
  `src/shared/domain/entities.py`. VO неоднородны: frozen `Email` нормализует значение,
  content blocks mutable. Не замораживай модели массово.
- Сохраняй domain-методы переходов/проверок (invitation consumption, notification mark-read),
  не обходи их присваиванием из API. Часть инвариантов — в services/policies; dataclass не ACL.
- DTO — преимущественно Pydantic по шаблону `src/<module>/application/dtos.py`.
  Сохраняй validation, enum и discriminated unions. `exclude_none=True` исключает и явный null,
  и default None: null не очищает поле. Для иной семантики проверь `model_fields_set`/`exclude_unset`
  и тесты потребителей; механическая смена флага меняет контракт.
- Protocol: `src/shared/application/repos.py`, `src/shared/domain/repos.py` и module repos.
  Проверяй конкретные сигнатуры/реализации, не только порт. У chat/practice составные ключи.
- `src/shared/infra/repos.py` и `src/shared/infra/database/repos/sqlalchemy.py` — разные семьи:
  `update(entity)` против `update(uid, **kwargs)`, разные mapper/search API. Не подменяй их по имени.

## DI, API и контроль доступа

- DI — `Depends`/`Annotated` по шаблону `src/<module>/dependencies/`; переиспользуй сборку.
  `DBSession`/`TransactionDep` в `src/shared/dependencies/database.py` разделяют сессию;
  тесты подменяют зависимости overrides/моками.
- `src/__init__.py` подключает верхние роутеры явно; внутри API-пакетов есть автопоиск
  через `src/shared/api/include_routers.py`. Перед добавлением endpoint проверь регистрацию,
  import-time эффекты и отсутствие дублей. `INSTALLED_MODULES` в `src/core/settings.py` — ORM/CLI,
  не регистрация HTTP. Сохраняй response DTO/dataclass, `Page`, body/query pagination и status/204.
- `CurrentIdentity` проверяет Bearer/JWT/blacklist по claims, не перечитывает memberships/права.
  `require_permissions`: по умолчанию любое право, `any_of=False` — все; это не resource ACL.
- `authorize` в `src/iam/application/policies/authorization.py`: без resource — permission;
  с policies — `any(policy(...))` без обязательной проверки кода; без policies — fallback к permission,
  не fail-closed. Проверяй зарегистрированные policies и требуемую комбинацию проверок.
- Применяй `CheckAccess`/policies курса, но course ownership не проверяет автоматически организацию,
  владельца session/chat/practice или связь переданных parent/child ID. Проследи scope до SQL.
  Защита неоднородна: не копируй отсутствие ACL у соседнего endpoint и не расширяй доступ.
- При auth-правках проверь user/M2M flows, типы токенов, refresh rotation/blacklist,
  membership/активность; для ACL — отказ, чужой ресурс и несвязанные parent/child ID.

## База данных, транзакции и события

- ORM: `src/core/database/base.py`, `Mapped`/relationships, PostgreSQL UUID/JSONB/Enum.
  При новом поле проверь обе стороны mapper и DTO; загрузи relationships до сериализации,
  без неявного async lazy-load. Изменение domain object не равно ORM update.
- `src/core/database/connection.py`: session factory закрывает сессию без auto-commit;
  autoflush/expire_on_commit выключены. Flush не commit; закрытие не сохраняет незакоммиченное.
- UoW Protocol уже есть в `src/shared/application/uow.py` и `src/shared/domain/repos.py`;
  стандартный DI передаёт `AsyncSession`. Commit — сервис/`Transaction`, не скрытый repo commit.
  `Transaction` не контекстный менеджер и не вызывает rollback: проверяй владельца сессии,
  при ошибке собственной транзакции обеспечь rollback перед продолжением работы.
- `src/shared/application/transaction.py`: collect events → optional recorder → commit → publish.
  Общий DI recorder не передаёт; очередь events опустошается. Ошибка publish не откатывает БД.
  Inbox/outbox модели не дают всеобщего exactly-once; учитывай записи/доставку при повторе.
- Для кешируемых данных проверь key/TTL/invalidation относительно commit; decorator не гарантия.
- Для порядка module/lesson учитывай `create_at`/`delete_and_compact`, constraints и parent links;
  проверь caller и блокировки: обычные create/delete не гарантируют compaction.
- `migrations/env.py` берёт URL из config и загружает `Base.metadata`; нестандартные модели
  импортируй явно. Меняя schema, добавляй revision, не правь применённую initial migration;
  проверь upgrade/downgrade, enum/FK/index/default, существующие строки/backfill и совместимость.
  Не запускай миграции/autogenerate на рабочей БД; create_all не проверяет Alembic chain.

## Асинхронность, ресурсы и интеграции

- I/O преимущественно async; тяжёлые блокирующие операции выноси в существующий executor/to_thread,
  как hashing/конвертацию. Не разделяй `AsyncSession` в параллельных задачах: дочернее сохранение
  генераторов использует отдельные `session_factory()` с commit/rollback; не считай все tools безопасными.
- Сохраняй `TaskGroup`/semaphores генераторов и event publisher, порядок результатов и ограниченный
  fan-out; не переписывай корректную конкурентность. Tools в `src/llm_service/services.py` используют
  `gather`, не гарантию TaskGroup-отмены siblings; учитывай частично выполненные эффекты.
- Не поглощай отмену текущей операции и не превращай её в успех. Cleanup — context manager/finally;
  собственную background task можно cancel → await с подавлением её ожидаемой `CancelledError`,
  как в `src/shared/infra/cache/in_memory.py`. Не оставляй задачи без владельца.
- Отмена coroutine/HTTP-ожидания не доказывает остановку удалённого router/provider-вызова;
  проверь каждую сетевую границу. SQL rollback не отменяет storage/SMTP/broker/HTTP эффекты.
- Для HTTP adapter проверь ClientSession lifecycle, status handling, timeout/retry/auth refresh;
  не закрывай общий клиент после запроса. Сохраняй проверки файла/upload owner/key, UUID не ACL.
- Config: BaseSettings и шаблон `src/core/*/config.py`; импорт `src/core/settings.py` загружает
  `.env`. Даже offline Alembic импортирует settings; импорт приложения не чистая операция.

## Taskiq и AI/LLM

- Broker/cancellation/metrics: `src/core/tkq/client.py`; Redis result backend не подключён.
  Tasks/labels: `src/courses/infra/tasks.py`; сохраняй names, DI и worker imports, их потребителей.
- Отмену generation tasks обеспечивает EDGE-декоратор; `src/core/tkq/middleware.py` не инициирует
  отмену, а исключает `TaskCancellationException` из retry и вычисляет label `retries_left`.
  Не смешивай эту библиотечную ошибку с `asyncio.CancelledError`.
- `.kiq()` → SQL generation session не атомарны; `generation_key` сейчас получает Taskiq task ID,
  но generation status и `CourseStatus` различны. Проследи весь путь до смены статусов.
- `LLMTextService`/`LLMImageService`, middleware и LangGraph: не обходи router SDK-вызовом
  без причины, теряя retry/учёт/контракты. У embeddings отдельный путь.
- Таймауты/повторы сверяй по уровням: tasks — `src/courses/infra/tasks.py`, internal HTTP —
  `src/shared/infra/services/config.py` и `src/shared/infra/services/client.py`, SDK —
  `src/core/providers/__init__.py`, router retry/backoff — `src/llm_router/utils.py`.
  SDK retries отключены; router различает OpenAI HTTP-статусы и прочие Exception. Не добавляй
  неограниченный retry; HTTP total timeout (секунды) может истечь раньше SDK/router-серии.
  Taskiq timeout не общий deadline цепочки; у model/tool loop нет общего deadline/лимита итераций.
  Оцени суммарный бюджет, tools, токены и отмену I/O, а не один timeout.
- Strict schema отправляется провайдеру через `src/llm_service/schemas.py`; router извлекает/
  восстанавливает JSON-object, предметную Pydantic validation выполняет потребитель до использования.
  Ошибка consumer validation вне router retry. Сохраняй `raw_text`/`output`; пустой structured
  ответ без tools и любой `incomplete` отклоняются.
- Responses history содержит reasoning/function_call/function_call_output/message: не своди её
  к тексту. Agent hooks — на invoke, model hooks — на model-итерацию, не каждую retry-попытку.
  Summarization не должна разрывать call/output; chat checkpoint сохраняется после полного loop,
  не гарантирует восстановление незавершённых tools.
- `src/courses/agents/course_generator/helper.py`: `snapshot.next` → resume с `None`;
  непустые values без next → сохранённый результат без нового input; иначе новый запуск.
  Сохраняй `durability="sync"` и thread keys из tasks/генераторов. Resume/повтор не regenerate:
  для новой генерации определи reset/versioning, включая дочерние threads. Checkpoint не mutex
  и не гарантия идемпотентности; `IntegrityError` сам по себе не предотвращает дубли эффектов.
- При изменении graph state проверь allowlist `src/courses/agents/course_generator/serializer.py`
  и TTL/единицы API checkpointer в `src/core/redis/__init__.py`, не только комментарий.
- Лимиты fan-out — в `src/courses/agents/course_generator/subagents/`, scope — экземпляр агента
  и его DI-переиспользование, не глобальная квота workers. Сохраняй сортировку и отдельные сессии.
- Indexing идёт отдельно после сохранения lesson; поиск знаний ограничивай `course_id`.
  Размерность/dense/sparse names меняй только с планом миграции: `src/core/retrieval/`,
  `src/courses/infra/database/repos/vector_repo.py`, collection setup в `src/core/lifespan.py`.

## Python, ошибки и наблюдаемость

- Сохраняй современные аннотации (`T | None`, `list[T]`, PEP 695 generics), Protocol,
  существующие dataclass/Pydantic роли моделей; не стирай полезные типы через `Any`/ignore.
- Стиль/импорты/исключения — `pyproject.toml` (Ruff); не дублируй конфиг и не форматируй соседний код.
- `DomainError` → `error.{code,message,details}`, не автоматически `public_message`;
  `ValueError` → 400 с `error.grant`, `HTTPException` → `detail`, request validation → 422.
  Не унифицируй форматы/публичные тексты без проверки клиентов.
- Используй существующие exceptions; не маскируй сбой сценария успехом. Task errors логируй
  и пробрасывай; структурированный tool error — отдельный контракт, не повод подавлять отмену.
- `logging.getLogger(__name__)`, JSON config — `src/core/logging.py`, middleware — request context.
  Не добавляй параллельные logger/print и полные чувствительные payload в обычные логи.
