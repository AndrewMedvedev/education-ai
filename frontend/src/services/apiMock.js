/**
 * Демонстрационный мок HTTP-слоя.
 *
 * Backend сейчас не запущен: каталог курсов (`POST /course/`) и карточка
 * курса отвечали 404, поэтому на странице «Рейтинг курсов…» показывалась
 * таблица с текстом ошибки `Not found`, а карточку курса открыть было нельзя.
 *
 * Этот модуль отвечает на read-запросы курсов, модулей и уроков локальными
 * данными. Подключается в `utils/api.js` и полностью отключается переменной
 * окружения, когда backend появится:
 *   VITE_USE_API_MOCK=false
 * По умолчанию мок включён, если адрес API не задан или указывает на localhost.
 */

const env = import.meta.env || {};
const configuredApiBase = env.VITE_API_BASE;
const explicitMockFlag = env.VITE_USE_API_MOCK;

function resolveMockEnabled() {
  if (explicitMockFlag !== undefined && explicitMockFlag !== "") {
    return String(explicitMockFlag).toLowerCase() === "true";
  }

  return !configuredApiBase || String(configuredApiBase).includes("localhost");
}

export const IS_API_MOCK = resolveMockEnabled();

const COURSE_ONE_ID = "11111111-1111-4111-8111-111111111111";
const COURSE_TWO_ID = "11111111-1111-4111-8111-111111111112";
const COURSE_THREE_ID = "11111111-1111-4111-8111-111111111113";

const MODULE_ONE_ID = "22222222-2222-4222-8222-222222222221";
const MODULE_TWO_ID = "22222222-2222-4222-8222-222222222222";
const LESSON_ONE_ID = "33333333-3333-4333-8333-333333333331";
const LESSON_TWO_ID = "33333333-3333-4333-8333-333333333332";

const THEORY_MARKDOWN = [
  "## Демонстрационный урок",
  "",
  "Этот текст отдаёт локальный мок: backend не запущен, данные лежат в",
  "`frontend/src/services/apiMock.js`.",
  "",
  "Что можно посмотреть в интерфейсе:",
  "",
  "- карточку курса: описание, сложность, цели обучения;",
  "- блок «Приглашения в курс» со списком и статусами;",
  "- повторную отправку и отмену приглашения.",
].join("\n");

function buildLessons() {
  return [
    {
      id: LESSON_ONE_ID,
      title: "Как устроен мок",
      description:
        "Разбираем, откуда берутся данные, пока backend не поднят.",
      order: 0,
      estimated_time_minutes: 12,
      learning_objectives: [
        "Понять, где живут демонстрационные данные",
        "Найти переменную окружения для отключения мока",
      ],
      content_blocks: [
        {
          id: "block-1",
          content_type: "text",
          md_content: THEORY_MARKDOWN,
          ai_generated: false,
        },
      ],
    },
    {
      id: LESSON_TWO_ID,
      title: "Приглашения в курс",
      description: "Как выглядит карта приглашений и что умеет.",
      order: 1,
      estimated_time_minutes: 8,
      learning_objectives: ["Проверить статусы приглашений"],
      content_blocks: [],
    },
  ];
}

function buildModules() {
  return [
    {
      id: MODULE_ONE_ID,
      module_id: MODULE_ONE_ID,
      title: "Знакомство с демо-режимом",
      description: "Первый модуль демонстрационного курса.",
      order: 0,
      duration: "1 неделя",
      learning_objectives: ["Осмотреться в интерфейсе"],
      lessons: buildLessons(),
      lesson_blocks: buildLessons(),
    },
    {
      id: MODULE_TWO_ID,
      module_id: MODULE_TWO_ID,
      title: "Приглашения и роли",
      description: "Модуль про карту приглашений.",
      order: 1,
      duration: "1 неделя",
      learning_objectives: ["Различать роли и статусы"],
      lessons: [],
      lesson_blocks: [],
    },
  ];
}

function buildCourse({
  id,
  title,
  description,
  difficulty,
  category,
  duration,
  format,
  tags,
  learningObjectives,
  withModules = false,
}) {
  const modules = withModules ? buildModules() : [];

  return {
    id,
    course_id: id,
    title,
    description,
    difficulty,
    category,
    duration,
    format,
    tags,
    status: "published",
    course_status: "published",
    learning_objectives: learningObjectives,
    modules,
    course_modules: modules,
  };
}

const DEMO_COURSES = [
  buildCourse({
    id: COURSE_ONE_ID,
    title: "Демо-курс: приглашения в курс",
    description:
      "Демонстрационный курс без backend. Откройте карточку курса и посмотрите блок «Приглашения в курс» ниже целей обучения.",
    difficulty: "beginner",
    category: "Демо",
    duration: "4 недели",
    format: "Теория + практика",
    tags: ["демо", "приглашения", "мок"],
    learningObjectives: [
      "Посмотреть карточку курса без backend",
      "Проверить статусы приглашений",
      "Отменить и повторить приглашение",
    ],
    withModules: true,
  }),
  buildCourse({
    id: COURSE_TWO_ID,
    title: "Онбординг преподавателя",
    description:
      "Короткий курс о том, как вести курс: модули, уроки, приглашения студентов.",
    difficulty: "intermediate",
    category: "Методика",
    duration: "2 недели",
    format: "Практика",
    tags: ["методика", "преподаватель"],
    learningObjectives: ["Настроить структуру курса"],
  }),
  buildCourse({
    id: COURSE_THREE_ID,
    title: "Продвинутая работа с приглашениями",
    description:
      "Роли, статусы и повторная отправка приглашений в демонстрационном режиме.",
    difficulty: "advanced",
    category: "Демо",
    duration: "3 недели",
    format: "Практика",
    tags: ["приглашения", "роли"],
    learningObjectives: ["Различать роли: студент, преподаватель, модератор"],
  }),
];

const DEMO_MODULES = buildModules();
const DEMO_LESSONS = buildLessons();

function findCourse(courseId) {
  const found = DEMO_COURSES.find((course) => course.id === courseId);
  if (found) return found;

  // Неизвестный id: отдаём первый демо-курс, чтобы любая ссылка открывалась.
  return { ...DEMO_COURSES[0], id: courseId, course_id: courseId };
}

const ROUTES = [
  {
    method: "POST",
    pattern: /^\/course\/?$/,
    handle: () => ({
      items: DEMO_COURSES,
      page: 1,
      size: 20,
      total: DEMO_COURSES.length,
      total_pages: 1,
    }),
  },
  {
    method: "POST",
    pattern: /^\/course\/my-courses\/?$/,
    handle: () => ({
      items: DEMO_COURSES,
      page: 1,
      size: 20,
      total: DEMO_COURSES.length,
      total_pages: 1,
    }),
  },
  {
    method: "GET",
    pattern: /^\/course\/basic\/info\/([^/]+)\/?$/,
    handle: (match) => findCourse(decodeURIComponent(match[1])),
  },
  {
    method: "GET",
    pattern: /^\/course\/edit\/([^/]+)\/?$/,
    handle: (match) => findCourse(decodeURIComponent(match[1])),
  },
  {
    method: "GET",
    pattern: /^\/course\/([^/]+)\/status\/?$/,
    handle: (match) => ({
      id: decodeURIComponent(match[1]),
      status: "published",
      course_status: "published",
    }),
  },
  {
    method: "GET",
    pattern: /^\/module\/basic\/info\/([^/]+)\/?$/,
    handle: (match) =>
      DEMO_MODULES.find((module) => module.id === decodeURIComponent(match[1])) ||
      DEMO_MODULES[0],
  },
  {
    method: "GET",
    pattern: /^\/lesson\/basic\/info\/([^/]+)\/?$/,
    handle: (match) =>
      DEMO_LESSONS.find((lesson) => lesson.id === decodeURIComponent(match[1])) ||
      DEMO_LESSONS[0],
  },
  {
    method: "GET",
    pattern: /^\/lesson\/theory\/([^/]+)\/?$/,
    handle: (match) => {
      const lesson =
        DEMO_LESSONS.find(
          (item) => item.id === decodeURIComponent(match[1]),
        ) || DEMO_LESSONS[0];
      return lesson.content_blocks;
    },
  },
];

function mockJson(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * Возвращает готовый Response для демо-режима или null, если запрос должен
 * уйти на реальный backend.
 */
export function resolveApiMock(path, options = {}) {
  if (!IS_API_MOCK || typeof path !== "string") return null;

  const cleanPath = String(path).split("?")[0];
  const method = String(options.method || "GET").toUpperCase();

  const route = ROUTES.find(
    (item) => item.method === method && item.pattern.test(cleanPath),
  );
  if (!route) return null;

  const match = cleanPath.match(route.pattern);
  return mockJson(route.handle(match));
}
