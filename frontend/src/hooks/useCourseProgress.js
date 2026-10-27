import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCourseLearningStructure } from "../services/courseService";
import {
  PROGRESS_STATUS,
  ensureCourseProgress,
  ensureLessonProgress,
  getLessonProgress,
  getLessonProgressStatus,
  getLessonsProgress,
  markLessonTheoryCompleted,
  syncCourseProgressPercent,
} from "../services/progressService";

// Практика и тест отмечаются на backend событием после проверки (асинхронно),
// поэтому после проверки несколько раз перечитываем прогресс урока.
const REFRESH_DELAYS_MS = [800, 1500, 3000, 5000, 8000];

const EMPTY_STATE = {
  isLoading: false,
  error: "",
  courseProgress: null,
  lessonProgressById: {},
  lessonIds: [],
  structure: null,
  hasLessonProgressErrors: false,
};

function wait(ms, signal) {
  return new Promise((resolve) => {
    if (signal?.aborted) {
      resolve(false);
      return;
    }
    const timeoutId = setTimeout(() => {
      signal?.removeEventListener("abort", handleAbort);
      resolve(true);
    }, ms);
    function handleAbort() {
      clearTimeout(timeoutId);
      resolve(false);
    }
    signal?.addEventListener("abort", handleAbort, { once: true });
  });
}

function getProgressErrorMessage(error) {
  return (
    error?.userMessage ||
    error?.message ||
    "Не удалось обновить прогресс курса."
  );
}

function collectLessonIds(course) {
  return (course?.blocks || []).flatMap((block) =>
    (block.lessons || []).map((lesson) => lesson.id).filter(Boolean),
  );
}

/**
 * Прогресс текущего ученика по курсу: создаёт записи прогресса курса/модуля/урока
 * при прохождении, загружает статусы уроков для дерева и процент прохождения.
 */
export function useCourseProgress(courseId, { enabled = true } = {}) {
  const [state, setState] = useState(EMPTY_STATE);
  const activeCourseIdRef = useRef(null);
  const lessonIdsRef = useRef([]);
  const lessonProgressRef = useRef({});
  const theoryRequestsRef = useRef(new Set());
  const refreshTokensRef = useRef({});
  const refreshControllersRef = useRef({});

  const isActive = useCallback(
    (targetCourseId) => activeCourseIdRef.current === targetCourseId,
    [],
  );

  const setLessonProgress = useCallback((lessonId, progress) => {
    lessonProgressRef.current = {
      ...lessonProgressRef.current,
      [lessonId]: progress,
    };
    setState((current) => ({
      ...current,
      lessonProgressById: {
        ...current.lessonProgressById,
        [lessonId]: progress,
      },
    }));
  }, []);

  const syncPercent = useCallback(
    async (targetCourseId) => {
      const total = lessonIdsRef.current.length;
      try {
        const courseProgress = await syncCourseProgressPercent(
          targetCourseId,
          total,
        );
        if (isActive(targetCourseId) && courseProgress) {
          setState((current) => ({ ...current, courseProgress }));
        }
      } catch (error) {
        if (isActive(targetCourseId)) {
          setState((current) => ({
            ...current,
            error: getProgressErrorMessage(error),
          }));
        }
      }
    },
    [isActive],
  );

  useEffect(() => {
    activeCourseIdRef.current = enabled && courseId ? courseId : null;
    lessonIdsRef.current = [];
    lessonProgressRef.current = {};
    theoryRequestsRef.current = new Set();
    Object.values(refreshControllersRef.current).forEach((controller) =>
      controller.abort(),
    );
    refreshTokensRef.current = {};
    refreshControllersRef.current = {};

    if (!enabled || !courseId) {
      setState(EMPTY_STATE);
      return undefined;
    }

    const controller = new AbortController();
    setState({ ...EMPTY_STATE, isLoading: true });

    async function load() {
      try {
        const [structure, courseProgress] = await Promise.all([
          getCourseLearningStructure(courseId),
          ensureCourseProgress(courseId),
        ]);
        const lessonIds = collectLessonIds(structure);
        let progressLoadError = null;
        const lessonProgressById = await getLessonsProgress(lessonIds, {
          signal: controller.signal,
          onError: (loadError) => {
            progressLoadError ||= loadError;
          },
        });
        if (controller.signal.aborted || !isActive(courseId)) return;

        lessonIdsRef.current = lessonIds;
        lessonProgressRef.current = {
          ...lessonProgressById,
          ...lessonProgressRef.current,
        };
        setState({
          isLoading: false,
          error: progressLoadError
            ? getProgressErrorMessage(progressLoadError)
            : "",
          courseProgress,
          lessonProgressById: lessonProgressRef.current,
          lessonIds,
          structure,
          hasLessonProgressErrors: Boolean(progressLoadError),
        });
        // Практика/тест могли закрыться событием, пока страница была закрыта, —
        // пересчитываем сохранённый процент курса.
        syncPercent(courseId);
      } catch (error) {
        if (controller.signal.aborted || !isActive(courseId)) return;
        setState((current) => ({
          ...current,
          isLoading: false,
          error:
            error?.userMessage ||
            error?.message ||
            "Не удалось загрузить прогресс курса.",
        }));
      }
    }

    load();

    return () => {
      controller.abort();
      if (activeCourseIdRef.current === courseId) {
        activeCourseIdRef.current = null;
      }
      Object.values(refreshControllersRef.current).forEach(
        (refreshController) => refreshController.abort(),
      );
      refreshControllersRef.current = {};
      refreshTokensRef.current = {};
    };
  }, [courseId, enabled, isActive, syncPercent]);

  const trackLesson = useCallback(
    async (moduleId, lessonId) => {
      const targetCourseId = activeCourseIdRef.current;
      if (!targetCourseId || !moduleId || !lessonId) return null;
      if (lessonProgressRef.current[lessonId]) {
        return lessonProgressRef.current[lessonId];
      }
      try {
        const progress = await ensureLessonProgress(
          targetCourseId,
          moduleId,
          lessonId,
        );
        if (isActive(targetCourseId) && progress) {
          setLessonProgress(lessonId, progress);
        }
        return progress;
      } catch (error) {
        if (isActive(targetCourseId)) {
          setState((current) => ({
            ...current,
            error: getProgressErrorMessage(error),
          }));
        }
        return null;
      }
    },
    [isActive, setLessonProgress],
  );

  const completeTheory = useCallback(
    async (moduleId, lessonId) => {
      const targetCourseId = activeCourseIdRef.current;
      if (!targetCourseId || !lessonId) return;
      if (lessonProgressRef.current[lessonId]?.theoryCompletedAt) return;
      if (theoryRequestsRef.current.has(lessonId)) return;
      theoryRequestsRef.current.add(lessonId);

      try {
        const trackedProgress = await trackLesson(moduleId, lessonId);
        if (!trackedProgress || !isActive(targetCourseId)) {
          theoryRequestsRef.current.delete(lessonId);
          return;
        }
        const progress = await markLessonTheoryCompleted(lessonId);
        if (!isActive(targetCourseId) || !progress) return;
        setLessonProgress(lessonId, progress);
        if (getLessonProgressStatus(progress) === PROGRESS_STATUS.COMPLETED) {
          syncPercent(targetCourseId);
        }
      } catch (error) {
        // Не получилось — дадим ещё одну попытку при следующей прокрутке до конца.
        theoryRequestsRef.current.delete(lessonId);
        if (isActive(targetCourseId)) {
          setState((current) => ({
            ...current,
            error: getProgressErrorMessage(error),
          }));
        }
      }
    },
    [isActive, setLessonProgress, syncPercent, trackLesson],
  );

  // field: "practiceCompletedAt" | "testCompletedAt" — что должно появиться после проверки.
  const refreshLesson = useCallback(
    async (lessonId, field) => {
      const targetCourseId = activeCourseIdRef.current;
      if (!targetCourseId || !lessonId) return;
      const token = Symbol(lessonId);
      refreshTokensRef.current[lessonId] = token;
      refreshControllersRef.current[lessonId]?.abort();
      const controller = new AbortController();
      refreshControllersRef.current[lessonId] = controller;
      let expectedFieldFound = !field;
      let lastError = null;

      for (const delay of REFRESH_DELAYS_MS) {
        const shouldContinue = await wait(delay, controller.signal);
        if (
          !shouldContinue ||
          !isActive(targetCourseId) ||
          refreshTokensRef.current[lessonId] !== token
        ) {
          return;
        }
        try {
          const progress = await getLessonProgress(lessonId, {
            signal: controller.signal,
          });
          lastError = null;
          if (!isActive(targetCourseId) || controller.signal.aborted) return;
          if (progress) setLessonProgress(lessonId, progress);
          if (!field || progress?.[field]) {
            expectedFieldFound = true;
            break;
          }
        } catch (error) {
          lastError = error;
        }
      }

      if (refreshControllersRef.current[lessonId] === controller) {
        delete refreshControllersRef.current[lessonId];
      }
      if (!expectedFieldFound && isActive(targetCourseId)) {
        setState((current) => ({
          ...current,
          error: lastError
            ? getProgressErrorMessage(lastError)
            : "Backend ещё не подтвердил обновление прогресса урока.",
        }));
      }
      if (expectedFieldFound && isActive(targetCourseId)) {
        syncPercent(targetCourseId);
      }
    },
    [isActive, setLessonProgress, syncPercent],
  );

  const summary = useMemo(() => {
    const total = state.lessonIds.length;
    const completed = state.lessonIds.filter(
      (lessonId) =>
        getLessonProgressStatus(state.lessonProgressById[lessonId]) ===
        PROGRESS_STATUS.COMPLETED,
    ).length;
    const started = state.lessonIds.filter(
      (lessonId) =>
        getLessonProgressStatus(state.lessonProgressById[lessonId]) !==
        PROGRESS_STATUS.NOT_STARTED,
    ).length;
    const calculatedPercent = total ? (completed * 100) / total : 0;
    const serverPercent = state.courseProgress?.percent;
    // Пока PATCH-пересчёт ещё не завершился, не показываем противоречие между
    // завершёнными LessonProgress и устаревшим сохранённым процентом.
    const percent = state.hasLessonProgressErrors
      ? Math.max(
          Number.isFinite(serverPercent) ? serverPercent : 0,
          calculatedPercent,
        )
      : Number.isFinite(serverPercent) &&
          Math.round(serverPercent) === Math.round(calculatedPercent)
        ? serverPercent
        : calculatedPercent;
    return {
      total,
      completed,
      started,
      percent: Math.min(100, Math.max(0, Math.round(percent))),
    };
  }, [
    state.courseProgress,
    state.hasLessonProgressErrors,
    state.lessonIds,
    state.lessonProgressById,
  ]);

  return {
    isEnabled: Boolean(enabled && courseId),
    isLoading: state.isLoading,
    error: state.error,
    lessonProgressById: state.lessonProgressById,
    // Полная структура курса (модули с уроками), по которой считается прогресс.
    structure: state.structure,
    summary,
    trackLesson,
    completeTheory,
    refreshLesson,
  };
}
