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

async function loadCourseSummary(courseId, signal) {
  const [structure, courseProgress] = await Promise.all([
    getCourseLearningStructure(courseId),
    getCourseProgress(courseId),
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

  const progressById = await getLessonsProgress(lessonIds, { signal });
  const records = lessonIds.map((lessonId) => progressById[lessonId]);
  const completedLessons = records.filter(
    (record) => getLessonProgressStatus(record) === PROGRESS_STATUS.COMPLETED,
  ).length;
  const startedLessons = records.filter(
    (record) => getLessonProgressStatus(record) !== PROGRESS_STATUS.NOT_STARTED,
  ).length;

  return {
    modulesCount,
    totalLessons: lessonIds.length,
    completedLessons,
    startedLessons,
    completedPractices: records.filter((record) => record?.practiceCompletedAt)
      .length,
    completedTests: records.filter((record) => record?.testCompletedAt).length,
    // Процент — тот, что сохранил backend; если его не пересчитывали, считаем сами.
    percent: Math.round(
      courseProgress.percent ||
        (lessonIds.length ? (completedLessons * 100) / lessonIds.length : 0),
    ),
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
  const [state, setState] = useState({ isLoading: false, byCourseId: {} });

  useEffect(() => {
    if (!enabled || courseIds.length === 0) {
      setState({ isLoading: false, byCourseId: {} });
      return undefined;
    }

    const controller = new AbortController();
    setState((current) => ({ ...current, isLoading: true }));

    async function load() {
      const byCourseId = {};
      // Курсы — по одному: внутри каждого и так идут параллельные запросы уроков.
      for (const courseId of courseIds) {
        if (controller.signal.aborted) return;
        try {
          byCourseId[courseId] = await loadCourseSummary(
            courseId,
            controller.signal,
          );
        } catch {
          byCourseId[courseId] = null;
        }
        if (!controller.signal.aborted) {
          setState({ isLoading: true, byCourseId: { ...byCourseId } });
        }
      }
      if (!controller.signal.aborted) {
        setState({ isLoading: false, byCourseId });
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
    byCourseId: state.byCourseId,
    totals,
    hasData: totals.coursesCount > 0,
  };
}
