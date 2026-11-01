import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCourseLearningStructure } from "../services/courseService";
import { useSessionStore } from "../stores/sessionStore";
import { hasSessionCredentials } from "../utils/api";
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
  const context = useSessionStore((session) => session.sessionContext);
  const authenticated = useSessionStore(hasSessionCredentials);
  const scope = useMemo(
    () => ({
      courseId,
      context,
      enabled: enabled && authenticated && Boolean(courseId),
    }),
    [courseId, context, enabled, authenticated],
  );
  const [storedState, setStoredState] = useState(EMPTY_STATE);
  const state = storedState.scope === scope ? storedState : EMPTY_STATE;
  const activeScopeRef = useRef(null);
  const lessonIdsRef = useRef([]);
  const lessonProgressRef = useRef({});
  const theoryRequestsRef = useRef(new Set());
  const refreshTokensRef = useRef({});
  const refreshControllersRef = useRef({});

  const isActive = useCallback(
    (target) =>
      target?.enabled &&
      activeScopeRef.current === target &&
      useSessionStore.getState().sessionContext === target.context &&
      hasSessionCredentials(useSessionStore.getState()),
    [],
  );

  const setState = useCallback(
    (update) => {
      const target = activeScopeRef.current;
      setStoredState((current) => {
        if (!isActive(target) || target.scope !== scope) return current;
        const next = typeof update === "function" ? update(current) : update;
        return { ...next, scope };
      });
    },
    [isActive, scope],
  );

  const setLessonProgress = useCallback(
    (lessonId, progress) => {
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
    },
    [setState],
  );

  const syncPercent = useCallback(
    async (target) => {
      if (!isActive(target)) return;
      const total = lessonIdsRef.current.length;
      try {
        const courseProgress = await syncCourseProgressPercent(
          target.courseId,
          total,
        );
        if (isActive(target) && courseProgress) {
          setState((current) => ({ ...current, courseProgress }));
        }
      } catch (error) {
        if (isActive(target)) {
          setState((current) => ({
            ...current,
            error: getProgressErrorMessage(error),
          }));
        }
      }
    },
    [isActive, setState],
  );

  useEffect(() => {
    // Отдельный запуск эффекта: даже повторный mount того же курса — не тот же запрос.
    const target = { ...scope, scope };
    activeScopeRef.current = target;
    lessonIdsRef.current = [];
    lessonProgressRef.current = {};
    theoryRequestsRef.current = new Set();
    Object.values(refreshControllersRef.current).forEach((controller) =>
      controller.abort(),
    );
    refreshTokensRef.current = {};
    refreshControllersRef.current = {};

    if (!scope.enabled) {
      setStoredState(EMPTY_STATE);
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
        if (controller.signal.aborted || !isActive(target)) return;
        const lessonIds = collectLessonIds(structure);
        let progressLoadError = null;
        const lessonProgressById = await getLessonsProgress(lessonIds, {
          signal: controller.signal,
          onError: (loadError) => {
            progressLoadError ||= loadError;
          },
        });
        if (controller.signal.aborted || !isActive(target)) return;

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
        syncPercent(target);
      } catch (error) {
        if (controller.signal.aborted || !isActive(target)) return;
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
      if (activeScopeRef.current === target) {
        activeScopeRef.current = null;
      }
      Object.values(refreshControllersRef.current).forEach(
        (refreshController) => refreshController.abort(),
      );
      refreshControllersRef.current = {};
      refreshTokensRef.current = {};
    };
  }, [courseId, scope, isActive, syncPercent, setState]);

  const trackLesson = useCallback(
    async (moduleId, lessonId) => {
      const target = activeScopeRef.current;
      if (
        !isActive(target) ||
        target.scope !== scope ||
        !moduleId ||
        !lessonId
      ) {
        return null;
      }
      if (lessonProgressRef.current[lessonId]) {
        return lessonProgressRef.current[lessonId];
      }
      try {
        const progress = await ensureLessonProgress(
          target.courseId,
          moduleId,
          lessonId,
        );
        if (isActive(target) && progress) {
          setLessonProgress(lessonId, progress);
        }
        return isActive(target) ? progress : null;
      } catch (error) {
        if (isActive(target)) {
          setState((current) => ({
            ...current,
            error: getProgressErrorMessage(error),
          }));
        }
        return null;
      }
    },
    [isActive, scope, setState, setLessonProgress],
  );

  const completeTheory = useCallback(
    async (moduleId, lessonId) => {
      const target = activeScopeRef.current;
      if (!isActive(target) || target.scope !== scope || !lessonId) return;
      if (lessonProgressRef.current[lessonId]?.theoryCompletedAt) return;
      if (theoryRequestsRef.current.has(lessonId)) return;
      const theoryRequests = theoryRequestsRef.current;
      theoryRequests.add(lessonId);

      try {
        const trackedProgress = await trackLesson(moduleId, lessonId);
        if (!trackedProgress || !isActive(target)) {
          theoryRequests.delete(lessonId);
          return;
        }
        const progress = await markLessonTheoryCompleted(lessonId);
        if (!isActive(target) || !progress) return;
        setLessonProgress(lessonId, progress);
        if (getLessonProgressStatus(progress) === PROGRESS_STATUS.COMPLETED) {
          syncPercent(target);
        }
      } catch (error) {
        // Не получилось — дадим ещё одну попытку при следующей прокрутке до конца.
        theoryRequests.delete(lessonId);
        if (isActive(target)) {
          setState((current) => ({
            ...current,
            error: getProgressErrorMessage(error),
          }));
        }
      }
    },
    [isActive, scope, setState, setLessonProgress, syncPercent, trackLesson],
  );

  // field: "practiceCompletedAt" | "testCompletedAt" — что должно появиться после проверки.
  const refreshLesson = useCallback(
    async (lessonId, field) => {
      const target = activeScopeRef.current;
      if (!isActive(target) || target.scope !== scope || !lessonId) return;
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
          !isActive(target) ||
          refreshTokensRef.current[lessonId] !== token
        ) {
          return;
        }
        try {
          const progress = await getLessonProgress(lessonId, {
            signal: controller.signal,
          });
          lastError = null;
          if (
            !isActive(target) ||
            controller.signal.aborted ||
            refreshTokensRef.current[lessonId] !== token
          )
            return;
          if (progress) setLessonProgress(lessonId, progress);
          if (!field || progress?.[field]) {
            expectedFieldFound = true;
            break;
          }
        } catch (error) {
          lastError = error;
        }
      }

      if (
        !isActive(target) ||
        controller.signal.aborted ||
        refreshTokensRef.current[lessonId] !== token
      )
        return;
      if (refreshControllersRef.current[lessonId] === controller) {
        delete refreshControllersRef.current[lessonId];
      }
      if (!expectedFieldFound && isActive(target)) {
        setState((current) => ({
          ...current,
          error: lastError
            ? getProgressErrorMessage(lastError)
            : "Backend ещё не подтвердил обновление прогресса урока.",
        }));
      }
      if (expectedFieldFound && isActive(target)) {
        syncPercent(target);
      }
    },
    [isActive, scope, setState, setLessonProgress, syncPercent],
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
    isEnabled: Boolean(scope.enabled),
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
