import { useEffect, useMemo, useState } from "react";
import { getCourseLearningStructure } from "../services/courseService";
import {
  PROGRESS_STATUS,
  getCourseProgress,
  getLessonProgressStatus,
  getLessonsProgress,
} from "../services/progressService";
import { isUuid } from "../utils/api";

function collectLessonIds(course) {
  return (course?.blocks || []).flatMap((block) =>
    (block.lessons || []).map((lesson) => lesson.id).filter(Boolean),
  );
}

function getProgressErrorMessage(error) {
  return (
    error?.userMessage ||
    error?.message ||
    "Не удалось загрузить прогресс курса."
  );
}

function clampPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.min(100, Math.max(0, number)) : 0;
}

async function loadCourseSummary(courseId, signal) {
  const [structure, courseProgress] = await Promise.all([
    getCourseLearningStructure(courseId),
    getCourseProgress(courseId, { signal }),
  ]);
  const lessonIds = collectLessonIds(structure);
  const modulesCount = (structure?.blocks || []).length;

  // Записи прогресса ещё нет — ученик курс не начинал, уроки не запрашиваем.
  if (!courseProgress) {
    return {
      modulesCount,
      totalLessons: lessonIds.length,
      completedLessons: 0,
      startedLessons: 0,
      completedPractices: 0,
      completedTests: 0,
      percent: 0,
    };
  }

  let progressLoadError = null;
  const progressById = await getLessonsProgress(lessonIds, {
    signal,
    onError: (error) => {
      progressLoadError ||= error;
    },
  });
  const records = lessonIds.map((lessonId) => progressById[lessonId]);
  const completedLessons = records.filter(
    (record) => getLessonProgressStatus(record) === PROGRESS_STATUS.COMPLETED,
  ).length;
  const startedLessons = records.filter(
    (record) => getLessonProgressStatus(record) !== PROGRESS_STATUS.NOT_STARTED,
  ).length;

  const calculatedPercent = lessonIds.length
    ? (completedLessons * 100) / lessonIds.length
    : 0;
  const serverPercent = clampPercent(courseProgress.percent);
  const percent = progressLoadError
    ? Math.max(serverPercent, calculatedPercent)
    : Math.round(serverPercent) === Math.round(calculatedPercent)
      ? serverPercent
      : calculatedPercent;

  return {
    modulesCount,
    totalLessons: lessonIds.length,
    completedLessons,
    startedLessons,
    completedPractices: records.filter((record) => record?.practiceCompletedAt)
      .length,
    completedTests: records.filter((record) => record?.testCompletedAt).length,
    percent: Math.round(clampPercent(percent)),
    error: progressLoadError ? getProgressErrorMessage(progressLoadError) : "",
  };
}

/**
 * Прогресс текущего пользователя по списку курсов (для профиля).
 * Ничего не создаёт на backend: только читает существующие записи прогресса.
 */
export function useMyCoursesProgress(courses, { enabled = true } = {}) {
  const courseIds = useMemo(
    () =>
      [...new Set((courses || []).map((course) => course?.id))].filter(isUuid),
    [courses],
  );
  const courseIdsKey = courseIds.join(",");
  const [state, setState] = useState({
    isLoading: false,
    isLoaded: false,
    byCourseId: {},
    errorsByCourseId: {},
  });

  useEffect(() => {
    if (!enabled || courseIds.length === 0) {
      setState({
        isLoading: false,
        isLoaded: enabled,
        byCourseId: {},
        errorsByCourseId: {},
      });
      return undefined;
    }

    const controller = new AbortController();
    setState({
      isLoading: true,
      isLoaded: false,
      byCourseId: {},
      errorsByCourseId: {},
    });

    async function load() {
      const byCourseId = {};
      const errorsByCourseId = {};
      // Курсы — по одному: внутри каждого и так идут параллельные запросы уроков.
      for (const courseId of courseIds) {
        if (controller.signal.aborted) return;
        try {
          const summary = await loadCourseSummary(courseId, controller.signal);
          byCourseId[courseId] = summary;
          if (summary.error) {
            errorsByCourseId[courseId] = summary.error;
          }
        } catch (error) {
          errorsByCourseId[courseId] = getProgressErrorMessage(error);
        }
        if (!controller.signal.aborted) {
          setState({
            isLoading: true,
            isLoaded: false,
            byCourseId: { ...byCourseId },
            errorsByCourseId: { ...errorsByCourseId },
          });
        }
      }
      if (!controller.signal.aborted) {
        setState({
          isLoading: false,
          isLoaded: true,
          byCourseId,
          errorsByCourseId,
        });
      }
    }

    load();
    return () => controller.abort();
    // courseIdsKey стабилен для одинакового набора курсов.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseIdsKey, enabled]);

  const totals = useMemo(() => {
    const summaries = Object.values(state.byCourseId).filter(Boolean);
    const sum = (key) =>
      summaries.reduce((total, summary) => total + (summary[key] || 0), 0);
    const totalLessons = sum("totalLessons");
    const completedLessons = sum("completedLessons");
    return {
      coursesCount: summaries.length,
      totalLessons,
      completedLessons,
      completedPractices: sum("completedPractices"),
      completedTests: sum("completedTests"),
      percent: totalLessons
        ? Math.round((completedLessons * 100) / totalLessons)
        : 0,
    };
  }, [state.byCourseId]);

  return {
    isLoading: state.isLoading,
    isLoaded: state.isLoaded,
    byCourseId: state.byCourseId,
    errorsByCourseId: state.errorsByCourseId,
    totals,
    hasData: totals.coursesCount > 0,
  };
}
