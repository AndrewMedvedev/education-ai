import { useEffect, useMemo, useState } from "react";
import { getCourseBasicInfo, isUuid } from "../utils/api";

/**
 * Число модулей для списка курсов (профиль, «Мои курсы»).
 * Списки /courses/my-courses и /members приходят без модулей, поэтому для каждого
 * курса читаем его краткую информацию (GET /courses/{id}) — запросы идут параллельно.
 * Возвращает { [courseId]: число модулей }; пока число не загружено, ключа нет.
 */
export function useCoursesModulesCount(courses, { enabled = true } = {}) {
  const courseIds = useMemo(
    () =>
      [...new Set((courses || []).map((course) => course?.id))].filter(isUuid),
    [courses],
  );
  const courseIdsKey = courseIds.join(",");
  const [counts, setCounts] = useState({});

  useEffect(() => {
    if (!enabled || courseIds.length === 0) return undefined;
    const controller = new AbortController();

    Promise.allSettled(
      courseIds.map((courseId) =>
        getCourseBasicInfo(courseId, { signal: controller.signal }).then(
          (course) => [courseId, (course?.blocks || []).length],
        ),
      ),
    ).then((results) => {
      if (controller.signal.aborted) return;
      setCounts((current) => {
        const next = { ...current };
        results.forEach((result) => {
          if (result.status === "fulfilled") {
            const [courseId, count] = result.value;
            next[courseId] = count;
          }
        });
        return next;
      });
    });

    return () => controller.abort();
    // courseIdsKey стабилен для одинакового набора курсов.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseIdsKey, enabled]);

  return counts;
}

const MODULE_FORMS = ["модуль", "модуля", "модулей"];

export function formatModulesCount(count) {
  const value = Math.max(0, Number(count) || 0);
  const mod10 = value % 10;
  const mod100 = value % 100;
  const form =
    mod10 === 1 && mod100 !== 11
      ? MODULE_FORMS[0]
      : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)
        ? MODULE_FORMS[1]
        : MODULE_FORMS[2];
  return `${value} ${form}`;
}
