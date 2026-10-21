## LLM Router: запросы и ответы

Дашборд `Application → LLM Router — Traces` читает
`public.llm_invocations` напрямую из PostgreSQL. Таблица должна уже существовать
в БД мониторинга LLM; эта задача не создаёт таблицы и не меняет backend.

В окружении Docker Compose задайте подключение к этой БД:

```dotenv
GRAFANA_LLM_DB_URL=postgres:5432
GRAFANA_LLM_DB_NAME=postgres
GRAFANA_LLM_DB_USER=grafana_llm_reader
GRAFANA_LLM_DB_PASSWORD=<пароль отдельного пользователя БД>
GRAFANA_LLM_DB_SSL_MODE=require
```

Для локального PostgreSQL без TLS используйте `GRAFANA_LLM_DB_SSL_MODE=disable`.
В контейнере адрес `localhost` указывает на саму Grafana, а не на PostgreSQL.
Пароли храните в локальном env или секретах окружения, не в Git.

Администратор БД должен создать пользователя только для чтения. В `psql`,
подключённом к нужной БД, достаточно выполнить:

```sql
CREATE USER grafana_llm_reader;
\password grafana_llm_reader
GRANT USAGE ON SCHEMA public TO grafana_llm_reader;
GRANT SELECT ON public.llm_invocations TO grafana_llm_reader;
```

После настройки пересоздайте Grafana, используя свой обычный env для Compose:

```sh
docker compose up -d --no-deps grafana-ai
```

Выберите период и нажмите «Открыть» слева у нужного запроса. Справа появятся
все вызовы с его `request_id`, отсортированные по дате сохранения. Выберите
вызов справа: маркер ▶ обозначает выбранный шаг, а панели Input и Output
показывают его полный запрос и ответ по уникальному `id`. Слева показаны
последние 500 групп за период; справа период не обрезает связанные вызовы.
Полный JSON доступен через просмотр значения ячейки, без обрезания.
При `failed` рядом с ответом показана ошибка.

LangSmith используется как референс «запрос → вызовы → Input / Output».
Это последовательность сохранённых вызовов, не дерево: в БД нет parent_id,
а дата записи через Rabbit не гарантирует порядок запуска или вложенность.
Его API, новые ручки backend и плагины Grafana не нужны. Ограничьте доступ к
Grafana: запросы и ответы могут содержать пользовательские данные.

## Метрики и запуск

Дашборды: Overview, FastAPI, PostgreSQL, Redis, RabbitMQ, Qdrant, Taskiq и LLM Router.
Панели сгруппированы по Health, Traffic, Errors, Latency, Capacity, Resources и Logs
там, где соответствующие данные доступны. Overview показывает сводку, а не
дублирует глубокую диагностику сервисов.

Используются только существующие метрики и поля `llm_invocations`:

- FastAPI: RPS, статусы, количество запросов, P50/P95/P99, активные запросы,
  средний размер request/response, top endpoint, Python process/GC.
- Taskiq: успешные/ошибочные попытки, результаты, очередь, consumers, unacked,
  текущий backlog общей dead-letter очереди AioPikaBroker,
  доля успешных завершённых попыток, среднее время и доступные процентили.
- PostgreSQL: connections/max_connections, транзакции, locks, cache hit,
  долгие транзакции, dead tuples, autovacuum, размеры БД/WAL и checkpoints.
- Redis: команды, клиенты, ключи, hit/miss, expiration/eviction, ошибки команд,
  задержки, slowlog, RDB/AOF, RSS и fragmentation.
- RabbitMQ: connections/channels/consumers, publish/deliver/ack, очереди,
  redelivery, dead-letter counters по причинам, alarms, watermark/FD utilization
  и свободный диск. Publish/deliver/ack берутся из глобальных counters, которые
  не исчезают при закрытии отдельного channel.
- Qdrant: REST/gRPC по операциям и статусам, error rate, P50/P95/P99,
  количество collections и суммарное количество vectors.
- LLM Router: скорость записи вызовов, failed rate, длительности, total tokens,
  статистика по моделям и прежний просмотр связанных request/response.

CPU, RAM, network, OOM, uptime контейнеров и блочный disk IOPS читаются из cAdvisor.
В LLM Router это ресурсы общего backend, а не выдуманный отдельный LLM-контейнер.
Диски Overview — файловые системы Docker host: на Docker Desktop это Linux VM.
Диск не суммируется по контейнерам, которые используют одно общее хранилище.

Не добавлены показатели без доступного источника: точное число рестартов,
CPU throttling, заполнение диска каждого сервиса, процент RAM при отсутствии
лимита, возраст сообщения, queue wait, Taskiq retry/timeout counters и точное
число выполняющихся задач/worker-процессов, PostgreSQL query latency/slow queries,
Qdrant collection-level capacity/backlog/replication, LLM TTFT, input/output tokens,
стоимость и связь с task/course. Новая бизнес-инструментация для них не добавлялась.

**Ограничения интерпретации:**

- Стандартные buckets Taskiq заканчиваются на 10 секундах. P50/P95/P99 скрываются,
  если percentile выходит за эту границу; для долгих задач доступно среднее.
- Unacked не равно точному числу выполняющихся задач. Ошибки Taskiq — ошибки
  попыток, а не обязательно окончательно failed задачи после retries.
- LLM `created_at` — время сохранения лога, `duration_ms` — длительность
  сохранённого вызова. Эти данные не измеряют HTTP RPS, TTFT или потоковые tokens/sec.
- Отсутствие измерений остаётся `No data`, а не заменяется фиктивным нулём.

Prometheus собирает HTTP-метрики с `backend:8000/metrics`, метрики Taskiq с
`taskiq:9000`, метрики БД через exporters, RabbitMQ через `/metrics/per-object`,
Qdrant через `/metrics`, ресурсы контейнеров через cAdvisor. Alloy отправляет
логи сервисов проекта в Loki с меткой `service`.

Используйте обычный корневой Compose и настроенное окружение проекта:

```sh
docker compose up -d --no-deps rabbitmq taskiq prometheus-ai loki-ai alloy alertmanager postgres-exporter redis-exporter cadvisor grafana-ai
```

Эта команда предполагает, что зависимости уже запущены, а образ backend собран.
**Не запускайте рабочий Taskiq для проверки без затрат на LLM**: он может получить
настоящую задачу генерации. Для такой проверки используйте только тестовые задачи
из `backend/tests/support/monitoring_smoke.py` и отдельную очередь `monitoring.smoke`.
Они не импортируют приложение, LLM-клиенты и ключи провайдеров.

При переносе с Dramatiq сначала завершите его текущие задачи и разберите старую
очередь: формат сообщений Taskiq другой, автоматического переноса нет.
Рабочая очередь Taskiq — `myapp_tasks`, параллельность по умолчанию — 25,
результаты Redis хранятся 10 минут. Таймаут генерации — 5 часов, при ошибке
параметры повторов заданы в `src/core/tkq.py` и `workflow.py`. Логика генерации и её контрольных точек не менялась.

В Compose нужны `POSTGRES_USERNAME`, `POSTGRES_PASSWORD`, `POSTGRES_DB`,
`POSTGRES_PORT`, `REDIS_PASSWORD`, `RABBIT_USERNAME`, `RABBIT_PASSWORD`,
`QDRANT_API_KEY` и параметры портов мониторинга. Если RabbitMQ использует
не стандартный `/`, задайте приложению `RABBIT_VIRTUALHOST` и создайте этот vhost
с нужными правами на стороне RabbitMQ.
`POSTGRES_PORT` используется PostgreSQL и его exporter; значения должны совпадать.
Приложению также нужны его обычные настройки из `.env.prod`.
Для другого файла окружения backend задайте `BACKEND_ENV_FILE` (путь относительно
каталога `docker`). Запуск приложения может выполнять его штатный bootstrap и
миграции; тесты мониторинга его не запускают.

В Prometheus откройте **Status → Target health**: ожидается `UP` для каждого
запущенного сервиса. В Grafana выберите соответствующий дашборд и период.
Отсутствие бизнес-запросов означает нулевые счётчики или отсутствие выборки
длительности, а не ошибку мониторинга. `up=0` означает недоступность цели;
`pg_up=0` / `redis_up=0` — проблему подключения exporter к БД.

## Алерты без внешних уведомлений

`prometheus/alerts.yml`: недоступность целей, доля HTTP 5xx выше 5%, p95 HTTP
выше 2 секунд, недоступность PostgreSQL и Redis. `loki/rules/backend-alerts.yml`:
более 5 ошибок ERROR/CRITICAL за 5 минут и появление CRITICAL за 10 минут.
Правила используют реальные имена метрик и JSON-поле `level` из логов backend.

Состояние правил видно в Prometheus **Alerts** и в Alertmanager
(`http://localhost:9093`). Правила Loki можно проверить через
`/loki/api/v1/rules`. Alertmanager объединяет события, но не отправляет почту,
Telegram или другие внешние уведомления. Это правила Prometheus/Loki,
не Grafana-managed rules.

## Проверки без LLM

Из каталога `backend`:

```sh
python -m pytest tests/unit/monitoring -q
```

Для проверки всех PromQL/LogQL запросов на поднятом стенде задайте
`TEST_GRAFANA_URL`, `TEST_GRAFANA_USER`, `TEST_GRAFANA_PASSWORD` и запустите
`tests/integration/test_monitoring_dashboards.py`. Проверка read-only: запросы
должны выполняться без ошибок, а Prometheus возвращать отсчёты.
Для изолированного воркера задайте `TEST_TASKIQ_QUEUE=monitoring.smoke`:
тесты проверят панели очереди на ней, не используя рабочую очередь.

`test_monitoring_taskiq.py` проверяет настоящий RabbitMQ/Redis через изолированный
воркер тестовых задач: успех, повтор после ошибки, таймаут и HTTP 200/400/500.
Для тестового контейнера нужны `MONITORING_CORE_PATH` (read-only каталог
`src/core`), `TEST_RABBIT_URL`, `TEST_REDIS_URL` (отдельная Redis DB),
`TASKIQ_QUEUE_NAME=monitoring.smoke` и `PROMETHEUS_MULTIPROC_DIR`.
На `PYTHONPATH` должен быть каталог `tests/support`. Запустите HTTP через
`uvicorn monitoring_smoke:app --host 0.0.0.0 --port 8000` и воркер через:

```sh
taskiq worker monitoring_smoke:broker --workers 1 --max-async-tasks 4 --ack-type when_saved
```

Если HTTP и worker находятся в разных контейнерах, передайте тестам
`TEST_TASKIQ_METRICS_URL=http://<worker>:9000`; по умолчанию используется localhost.

Запускайте тесты в том же изолированном окружении; его порты HTTP/метрик — 8000/9000.
После проверки удалите тестовый контейнер, чтобы он не подменял рабочие цели.
`test_monitoring_qdrant.py` при заданном `TEST_QDRANT_URL` и `TEST_QDRANT_API_KEY`
проверяет REST/gRPC на своей пустой временной коллекции и удаляет её в `finally`.
Ни эти тесты, ни тестовые задачи не вызывают LLM и не применяют миграции PostgreSQL.

