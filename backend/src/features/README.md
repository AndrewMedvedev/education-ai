# Модуль `features`

## 1. Название и краткое описание

`features` содержит набор standalone scripts/utilities для подготовки AI-моделей, загрузки курса из JSON, парсинга файлов и ручного запуска генерации. По коду это не REST-модуль, а вспомогательная зона для экспериментов/seed-операций.

## 2. Границы ответственности

**Делает:** парсит документы в дерево, запускает seed/update AI models, загружает course JSON, содержит ручные сценарии. **Не делает:** не предоставляет FastAPI endpoints, не содержит собственных ORM tables.

## 3. Глоссарий

| Термин | Значение |
|---|---|
| `TreeNode` | Узел дерева распарсенного документа. |
| Seed script | Скрипт наполнения/обновления данных, например AI models. |

## 4. Структура папок

```text
backend/src/features/
├── add_ai_models.py       # seed/update AI models
├── add_course.py          # загрузка course.json в доменные сущности courses
├── dependencies.py        # file parser/tree builder utilities
├── schemas.py             # фактически script для course generator/Qdrant
├── test.py                # ручной script lesson builder
└── requirements.md        # требования/описание
```

## 5. Доменная модель

Собственной доменной модели нет. `TreeNode` в `dependencies.py` содержит `name`, `node_type`, `level`, `content`, `children` и методы `add_child`, `to_dict`, `print_tree`, `count_nodes`.

## 6. Ключевые сценарии (use cases)

| Сценарий | Входные данные | Шаги | Результат | Ошибки |
|---|---|---|---|---|
| Парсинг файла | path | определить формат → parser → tree | `TreeNode`/dict | `FileNotFoundError`, `ValueError`, `ImportError` |
| Seed AI models | список моделей в script | открыть DB session → repository create/update | records в `ai_models` | DB/runtime |
| Загрузка курса | `course_result.json`/JSON | создать Course/Module/Lesson | записи courses | DB/runtime |

## 7. Публичный API модуля

Не применимо: FastAPI endpoints в `features` не найдены.

Внутренние контракты: scripts напрямую используют `courses`, `llm_router`, `core.database`, Qdrant и LangChain runtime.

## 8. События

Не применимо: собственные domain/integration events не найдены.

## 9. Хранение данных

Собственных таблиц нет. Scripts пишут в таблицы других модулей (`ai_models`, courses tables).

## 10. Зависимости

`markitdown`, `python-docx`, `python-pptx`, `pdfplumber`, `lxml`, `courses`, `llm_router`, `core.database`, Qdrant, LangChain.

## 11. Конфигурация

| Параметр | Назначение | Значение по умолчанию | Обязательность |
|---|---|---|---|
| Пути к JSON/results | Входные данные scripts | Захардкожены в scripts | Для ручного запуска |
| UUID course/user | Ручные сценарии генерации | Захардкожены | Требуют проверки перед запуском |

## 12. Фоновые процессы

Не применимо: jobs/schedulers нет; scripts запускаются вручную.

## 13. Безопасность и права доступа

Не применимо для API. Scripts обходят HTTP/IAM и работают напрямую с БД/сервисами.

## 14. Каталог ошибок модуля и их HTTP-статусов

### a) Единый формат ошибки

Не применяется напрямую, так как HTTP endpoints нет. Если utilities будут вызваны из API, `ValueError` обработается shared handler как 400.

### b) Таблица ошибок

| Ошибка | HTTP | Когда | Где |
|---|---:|---|---|
| `FileNotFoundError` | не HTTP | Файл отсутствует | `dependencies.py` |
| `ValueError` | 400 при вызове из API | Неизвестный/неподдержанный формат | `dependencies.py` |
| `ImportError` | не HTTP | Нет parser library | `dependencies.py` |
| DB/runtime | 500 при вызове из API | Ошибки scripts | scripts |

### c) Правила маппинга

Собственного маппинга нет.

### d) Формат ошибок валидации

Не применимо.

## 15. Тестирование

Отдельных pytest-тестов не найдено. `test.py` — manual script, а не unit test.

## 16. Как с этим работать разработчику

Перед запуском scripts вручную проверьте hardcoded paths/UUID и окружение БД/Qdrant. Не используйте эти scripts как production API без оборачивания в сервисы и явной обработки ошибок.

## 17. Наблюдения и технический долг

- `dependencies.py` содержит file parser, а не зависимости FastAPI.
- `schemas.py` содержит исполняемый script, не schemas.
- В scripts есть hardcoded UUID, prompts и paths.
- `add_ai_models.py` выглядит как seed management, но не оформлен как migration/command.

## 18. Открытые вопросы

- Является ли `features` production-модулем или песочницей?
- Какие scripts должны быть поддерживаемыми командами CLI?
