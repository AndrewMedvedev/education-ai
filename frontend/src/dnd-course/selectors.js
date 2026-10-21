import { getLessonBlocks, nodeId } from "./helpers";

export function getStats(state) {
  const assigned = new Set(state.modules.flatMap((module) => module.lessonIds));
  const unassignedLessons = state.lessons.filter((lesson) => !assigned.has(lesson.id));
  const nonEmptyModules = state.modules.filter((module) => module.lessonIds.length > 0);
  return {
    materials: state.materials.length,
    readyMaterials: state.materials.filter((item) => item.status === "ready").length,
    errorMaterials: state.materials.filter((item) => item.status === "error").length,
    uploadingMaterials: state.materials.filter((item) => item.status === "uploading").length,
    unusedMaterials: state.materials.filter(
      (item) => item.status === "ready" && !item.lessonId,
    ).length,
    lessons: state.lessons.length,
    modules: state.modules.length,
    unassignedLessons: unassignedLessons.length,
    emptyModules: state.modules.length - nonEmptyModules.length,
    nonEmptyModules: nonEmptyModules.length,
  };
}

export function getProgress(state) {
  const stats = getStats(state);
  const steps = [
    { id: "course", label: "Карточка курса", done: Boolean(state.course?.id) },
    { id: "materials", label: "Материалы", done: stats.readyMaterials > 0 || stats.lessons > 0 },
    { id: "lessons", label: "Уроки", done: stats.lessons > 0 },
    { id: "modules", label: "Модули", done: stats.nonEmptyModules > 0 },
  ];
  let doneCount = 0;
  for (const step of steps) {
    if (!step.done) break;
    doneCount += 1;
  }
  return {
    steps,
    doneCount,
    percent: doneCount * 25,
    currentStep: Math.min(doneCount + 1, steps.length),
  };
}

export function getProblems(state) {
  const stats = getStats(state);
  const problems = [];
  const assigned = new Set(state.modules.flatMap((module) => module.lessonIds));
  state.lessons
    .filter((lesson) => !assigned.has(lesson.id))
    .forEach((lesson) =>
      problems.push({
        id: `unassigned:${lesson.id}`,
        nodeId: nodeId.lesson(lesson.id),
        severity: "warning",
        text: `«${lesson.title}» без модуля — сохранится на сервере и попадёт в курс, только когда вы добавите его в модуль`,
      }),
    );
  state.modules
    .filter((module) => module.lessonIds.length === 0)
    .forEach((module) =>
      problems.push({
        id: `empty:${module.id}`,
        nodeId: nodeId.module(module.id),
        severity: "warning",
        text: `Модуль «${module.title}» пустой`,
      }),
    );
  state.materials
    .filter((item) => item.status === "error")
    .forEach((item) =>
      problems.push({
        id: `error:${item.id}`,
        nodeId: nodeId.material(item.id),
        severity: "warning",
        text: `Материал «${item.fileName}» не обработан`,
      }),
    );
  state.materials
    .filter((item) => item.status === "ready" && !item.lessonId)
    .forEach((item) =>
      problems.push({
        id: `unused:${item.id}`,
        nodeId: nodeId.material(item.id),
        severity: "info",
        text: `Материал «${item.fileName}» не добавлен в урок`,
      }),
    );
  state.lessons
    .filter((lesson) => !lesson.title?.trim() || !lesson.description?.trim())
    .forEach((lesson) =>
      problems.push({
        id: `fields:${lesson.id}`,
        nodeId: nodeId.lesson(lesson.id),
        severity: "warning",
        text: `У урока «${lesson.title || "без названия"}» не заполнены обязательные поля`,
      }),
    );
  Object.entries(state.forms || {}).forEach(([key]) =>
    problems.push({
      id: `form:${key}`,
      nodeId: key,
      severity: "warning",
      text: "Есть несохранённые изменения в инспекторе",
    }),
  );
  if (stats.uploadingMaterials > 0 || hasBlockingPending(state)) {
    problems.push({
      id: "pending",
      nodeId: null,
      severity: "blocking",
      text: "Дождитесь завершения текущих операций",
    });
  }
  return problems;
}

export function hasBlockingPending(state) {
  return Object.keys(state.pending || {}).some((key) => key !== "finish") ||
    Object.entries(state.saveStatus || {}).some(
      ([key, status]) => key.endsWith(":content") && (status === "saving" || status === "dirty"),
    );
}

export function getNextTask(state) {
  const stats = getStats(state);
  if (!state.course?.id) return "Создайте карточку курса";
  if (stats.readyMaterials === 0 && stats.lessons === 0) return "Загрузите первый материал";
  if (stats.lessons === 0) return "Перетащите материалы в урок";
  if (stats.nonEmptyModules === 0 || stats.unassignedLessons > 0) return "Добавьте урок в модуль";
  if (stats.emptyModules > 0 || stats.errorMaterials > 0) return "Проверьте структуру курса";
  return "Курс готов к завершению";
}

export function canFinish(state) {
  const stats = getStats(state);
  return (
    Boolean(state.course?.id) &&
    stats.nonEmptyModules > 0 &&
    !hasBlockingPending(state)
  );
}

export function getGlobalSaveState(state) {
  const statuses = Object.values(state.saveStatus || {});
  if (hasBlockingPending(state) || statuses.includes("saving")) return "saving";
  if (statuses.includes("error")) return "error";
  if (statuses.includes("dirty")) return "dirty";
  return "saved";
}

/** Какие узлы подходят под фильтр палитры. */
export function matchFilter(filter, type, entity, state) {
  if (!filter) return true;
  switch (filter) {
    case "all":
      return type === "material";
    case "ready":
      return type === "material" && entity.status === "ready" && !entity.lessonId;
    case "errors":
      return type === "material" && entity.status === "error";
    case "unassigned":
      return type === "lesson" && !state.modules.some((module) => module.lessonIds.includes(entity.id));
    case "modules":
      return type === "module";
    case "incomplete":
      if (type === "material") return entity.status !== "ready" || !entity.lessonId;
      if (type === "lesson")
        return (
          getLessonBlocks(entity).length === 0 ||
          !state.modules.some((module) => module.lessonIds.includes(entity.id))
        );
      if (type === "module") return entity.lessonIds.length === 0 || !entity.description;
      return false;
    default:
      return true;
  }
}
