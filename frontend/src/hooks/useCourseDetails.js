import { useEffect, useRef, useState } from "react";
import { createDetailLoader } from "../course/detailLoader.js";
import {
  mergeCourse,
  mergeModule,
  mergeLesson,
} from "../course/courseState.js";
import {
  getCourse,
  getModuleBasicInfo,
  getLessonBasicInfo,
  isUuid,
} from "../utils/api";
import { useSessionStore } from "../stores/sessionStore";

const IDLE = { loading: false, error: "" };
const errorMessage = (error) =>
  error?.userMessage ||
  error?.message ||
  "Не удалось загрузить содержимое курса.";

export function useCourseDetails({
  courseId,
  lessonId,
  courses,
  enabled,
  context,
  setCourses,
  pathname,
}) {
  const available = Boolean(
    enabled && courseId && pathname.startsWith("/course/"),
  );
  const scopeRef = useRef(null);
  const previous = scopeRef.current;
  if (
    !previous ||
    previous.context !== context ||
    previous.courseId !== courseId ||
    previous.available !== available
  ) {
    // Identity changes during render block late writes even before effect cleanup.
    scopeRef.current = {
      context,
      courseId,
      available,
      loader: createDetailLoader(),
      active: false,
    };
  }
  const scope = scopeRef.current;
  const current = () =>
    scopeRef.current === scope &&
    scope.active &&
    scope.available &&
    useSessionStore.getState().sessionContext === context;
  const [state, setState] = useState(null);
  const [attempt, retry] = useState(0);
  const update = (part, value) => {
    if (!current()) return;
    setState((prev) => {
      if (!current()) return prev;
      const base =
        prev?.scope === scope ? prev : { scope, course: IDLE, content: IDLE };
      return { ...base, [part]: value };
    });
  };
  const applyCourses = (merge) => {
    if (current()) setCourses((prev) => (current() ? merge(prev) : prev));
  };

  useEffect(() => {
    scope.active = true;
    return () => {
      scope.active = false;
      scope.loader.reset();
    };
  }, [scope]);

  useEffect(() => {
    if (!current()) return;
    let active = true;
    update("course", { loading: true, error: "" });
    scope.loader
      .run(
        `course:${courseId}`,
        () => (current() ? getCourse(courseId) : undefined),
        (course) => applyCourses((prev) => mergeCourse(prev, course)),
      )
      .then(
        () => {
          if (active) update("course", { ...IDLE, ready: true });
        },
        (error) => {
          if (active)
            update("course", { loading: false, error: errorMessage(error) });
        },
      );
    return () => {
      active = false;
    };
  }, [scope, attempt, setCourses]);

  const course = courses.find((item) => item.id === courseId);
  const hasCourse = Boolean(course);
  // Merges replace course objects. Depend on structure, not those object refs:
  // a successful sibling must not automatically retry a failed module.
  const moduleIds = JSON.stringify(
    (course?.blocks || []).map((block) => block.id).filter(isUuid),
  );
  useEffect(() => {
    if (!current() || !hasCourse) return;
    let active = true;
    update("content", { loading: true, error: "" });
    async function load() {
      const results = await Promise.allSettled(
        JSON.parse(moduleIds).map((id) =>
          scope.loader.run(
            `module:${id}`,
            () => (current() ? getModuleBasicInfo(id) : undefined),
            (module) =>
              applyCourses((prev) =>
                prev.map((item) =>
                  item.id === courseId ? mergeModule(item, module) : item,
                ),
              ),
          ),
        ),
      );
      if (!active || !current()) return;
      const failed = results.find((result) => result.status === "rejected");
      if (failed) throw failed.reason;
      if (isUuid(lessonId)) {
        await scope.loader.run(
          `lesson:${lessonId}`,
          () => (current() ? getLessonBasicInfo(lessonId) : undefined),
          (lesson) =>
            applyCourses((prev) =>
              prev.map((item) =>
                item.id === courseId ? mergeLesson(item, lesson) : item,
              ),
            ),
        );
      }
      if (active) update("content", { ...IDLE, ready: true });
    }
    load().catch((error) => {
      if (active)
        update("content", { loading: false, error: errorMessage(error) });
    });
    return () => {
      active = false;
    };
  }, [scope, hasCourse, moduleIds, lessonId, attempt, setCourses]);

  const visible = available && state?.scope === scope ? state : null;
  return {
    loading: Boolean(visible?.course.loading || visible?.content.loading),
    error: visible?.course.error || visible?.content.error || "",
    ready: Boolean(visible?.course.ready && visible?.content.ready),
    retry: () => {
      if (current()) retry((value) => value + 1);
    },
  };
}
