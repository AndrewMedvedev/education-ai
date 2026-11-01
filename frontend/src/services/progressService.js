import {
  ApiError,
  getSessionContext,
  completeLessonTheory,
  createCourseProgress,
  createLessonProgress,
  createModuleProgress,
  fetchCourseProgress,
  fetchLessonProgress,
  fetchModuleProgress,
  recalculateCourseProgress,
} from "../utils/api";

// Статусы прохождения урока/модуля для отрисовки цветами.
export const PROGRESS_STATUS = {
  NOT_STARTED: "not_started",
  IN_PROGRESS: "in_progress",
  COMPLETED: "completed",
};

export const PROGRESS_STATUS_LABELS = {
  [PROGRESS_STATUS.NOT_STARTED]: "Не начат",
  [PROGRESS_STATUS.IN_PROGRESS]: "В процессе",
  [PROGRESS_STATUS.COMPLETED]: "Пройден",
};

const LESSON_PROGRESS_CONCURRENCY = 4;
const pendingRequests = new Map();
let pendingContext = getSessionContext();

function assertContext(context) {
  if (context !== getSessionContext()) {
    throw new ApiError("Контекст сессии изменился.", { code: "STALE_SESSION" });
  }
}

function isStatus(error, status) {
  return Number(error?.status) === status;
}

// Один и тот же запрос (например, создание прогресса урока) не отправляем дважды,
// пока первый ещё в полёте: эффекты React в StrictMode вызываются повторно.
function once(key, factory) {
  const context = getSessionContext();
  if (pendingContext !== context) {
    pendingRequests.clear();
    pendingContext = context;
  }
  if (pendingRequests.has(key)) {
    return pendingRequests.get(key);
  }
  const promise = factory(context)
    .then((result) => {
      assertContext(context);
      return result;
    })
    .finally(() => {
      // Старый запрос не должен удалить новый singleflight с тем же ID.
      if (pendingRequests.get(key) === promise) pendingRequests.delete(key);
    });
  pendingRequests.set(key, promise);
  return promise;
}

export function normalizeCourseProgress(raw) {
  if (!raw || typeof raw !== "object") return null;
  const percent = Number(raw.progress_percent ?? raw.progressPercent ?? 0);
  return {
    id: raw.id || "",
    courseId: raw.course_id || raw.courseId || "",
    userId: raw.user_id || raw.userId || "",
    percent: Number.isFinite(percent) ? Math.min(100, Math.max(0, percent)) : 0,
  };
}

export function normalizeLessonProgress(raw) {
  if (!raw || typeof raw !== "object") return null;
  return {
    id: raw.id || "",
    lessonId: raw.lesson_id || raw.lessonId || "",
    moduleProgressId: raw.module_progress_id || raw.moduleProgressId || "",
    theoryCompletedAt: raw.theory_completed_at ?? raw.theoryCompletedAt ?? null,
    practiceCompletedAt:
      raw.practice_completed_at ?? raw.practiceCompletedAt ?? null,
    testCompletedAt: raw.test_completed_at ?? raw.testCompletedAt ?? null,
  };
}

// Урок считается пройденным, когда закрыты теория, практика и проверочные
// вопросы — так же считает backend при пересчёте процента курса.
export function getLessonProgressStatus(progress) {
  if (!progress) return PROGRESS_STATUS.NOT_STARTED;
  const parts = [
    progress.theoryCompletedAt,
    progress.practiceCompletedAt,
    progress.testCompletedAt,
  ];
  const done = parts.filter(Boolean).length;
  if (done === parts.length) return PROGRESS_STATUS.COMPLETED;
  return done > 0 ? PROGRESS_STATUS.IN_PROGRESS : PROGRESS_STATUS.NOT_STARTED;
}

export function getModuleProgressSummary(block, lessonProgressById = {}) {
  const lessons = block?.lessons || [];
  let completed = 0;
  let started = 0;
  lessons.forEach((lesson) => {
    const status = getLessonProgressStatus(lessonProgressById[lesson.id]);
    if (status === PROGRESS_STATUS.COMPLETED) completed += 1;
    if (status !== PROGRESS_STATUS.NOT_STARTED) started += 1;
  });

  let status = PROGRESS_STATUS.NOT_STARTED;
  if (lessons.length > 0 && completed === lessons.length) {
    status = PROGRESS_STATUS.COMPLETED;
  } else if (started > 0) {
    status = PROGRESS_STATUS.IN_PROGRESS;
  }

  return { total: lessons.length, completed, started, status };
}

export async function getCourseProgress(courseId, options = {}) {
  try {
    return normalizeCourseProgress(
      await fetchCourseProgress(courseId, options),
    );
  } catch (error) {
    if (isStatus(error, 404)) return null;
    throw error;
  }
}

export async function getLessonProgress(lessonId, options = {}) {
  try {
    return normalizeLessonProgress(
      await fetchLessonProgress(lessonId, options),
    );
  } catch (error) {
    if (isStatus(error, 404)) return null;
    throw error;
  }
}

// GET → при 404 POST → при 409 (запись создалась параллельно) снова GET.
async function ensureRecord({ read, create }, context) {
  assertContext(context);
  try {
    const record = await read();
    assertContext(context);
    return record;
  } catch (error) {
    assertContext(context);
    if (!isStatus(error, 404)) throw error;
  }
  try {
    const record = await create();
    assertContext(context);
    return record;
  } catch (error) {
    assertContext(context);
    if (isStatus(error, 409)) {
      const record = await read();
      assertContext(context);
      return record;
    }
    throw error;
  }
}

export function ensureCourseProgress(courseId) {
  return once(`course:${courseId}`, async (context) =>
    normalizeCourseProgress(
      await ensureRecord(
        {
          read: () => fetchCourseProgress(courseId),
          create: () => createCourseProgress(courseId),
        },
        context,
      ),
    ),
  );
}

export function ensureModuleProgress(courseId, moduleId) {
  return once(`module:${moduleId}`, async (context) => {
    await ensureCourseProgress(courseId);
    assertContext(context);
    return ensureRecord(
      {
        read: () => fetchModuleProgress(moduleId),
        create: () => createModuleProgress(courseId, moduleId),
      },
      context,
    );
  });
}

export function ensureLessonProgress(courseId, moduleId, lessonId) {
  return once(`lesson:${lessonId}`, async (context) => {
    await ensureModuleProgress(courseId, moduleId);
    assertContext(context);
    return normalizeLessonProgress(
      await ensureRecord(
        {
          read: () => fetchLessonProgress(lessonId),
          create: () => createLessonProgress(moduleId, lessonId),
        },
        context,
      ),
    );
  });
}

export async function markLessonTheoryCompleted(lessonId) {
  return normalizeLessonProgress(await completeLessonTheory(lessonId));
}

export async function syncCourseProgressPercent(courseId, totalLessons) {
  return normalizeCourseProgress(
    await recalculateCourseProgress(courseId, totalLessons),
  );
}

// Отдельной ручки «весь прогресс курса» на backend нет, поэтому прогресс уроков
// для дерева запрашиваем по одному с ограничением параллельности.
export async function getLessonsProgress(lessonIds, { signal, onError } = {}) {
  const context = getSessionContext();
  const ids = [...new Set((lessonIds || []).filter(Boolean))];
  const result = {};
  let cursor = 0;

  async function worker() {
    while (cursor < ids.length) {
      assertContext(context);
      if (signal?.aborted) return;
      const lessonId = ids[cursor];
      cursor += 1;
      try {
        result[lessonId] = await getLessonProgress(lessonId, { signal });
        assertContext(context);
      } catch (error) {
        assertContext(context);
        // Только 404 нормализуется getLessonProgress в отсутствие записи.
        // Остальные ошибки не должны выглядеть как «урок не начат».
        result[lessonId] = null;
        onError?.(error, lessonId);
      }
    }
  }

  await Promise.all(
    Array.from(
      { length: Math.min(LESSON_PROGRESS_CONCURRENCY, ids.length) },
      worker,
    ),
  );
  assertContext(context);
  return result;
}
