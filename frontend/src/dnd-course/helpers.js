import { MAX_CONTENT_BLOCKS } from "../lesson/lessonEditorConfig";

export { MAX_CONTENT_BLOCKS };

export const nodeId = {
  course: () => "course",
  material: (id) => `material:${id}`,
  lesson: (id) => `lesson:${id}`,
  module: (id) => `module:${id}`,
};

export function parseNodeId(id) {
  if (!id) return { type: null, entityId: null };
  if (id === "course") return { type: "course", entityId: "course" };
  const index = id.indexOf(":");
  if (index < 0) return { type: null, entityId: null };
  return { type: id.slice(0, index), entityId: id.slice(index + 1) };
}

export function createLocalId(prefix) {
  const random =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${random}`;
}

export function parseObjectives(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function objectivesToText(value) {
  return Array.isArray(value) ? value.join("\n") : String(value || "");
}

export function parseTags(value) {
  return String(value || "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export function tagsToText(tags) {
  return Array.isArray(tags) ? tags.join(", ") : String(tags || "");
}

export function materialToContentBlock(material) {
  return {
    content_type: "text",
    ai_generated: false,
    md_content: material?.markdown || "",
  };
}

export function materialsToContentBlocks(materials) {
  return materials
    .map(materialToContentBlock)
    .filter((block) => block.md_content.trim());
}

export function getLessonBlocks(lesson) {
  return lesson?.contentBlocks || lesson?.content_blocks || [];
}

export function getFileKind(fileName = "") {
  const match = /\.([a-z0-9]+)$/i.exec(fileName);
  return match ? match[1].toUpperCase() : "Файл";
}

export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

export function markdownExcerpt(markdown, limit = 150) {
  const text = String(markdown || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[[^\]]*]\([^)]*\)/g, " ")
    .replace(/\[([^\]]*)]\([^)]*\)/g, "$1")
    .replace(/[#>*_`|~-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return text.length > limit ? `${text.slice(0, limit).trimEnd()}…` : text;
}

export function pluralize(count, [one, few, many]) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function countLabel(count, forms) {
  return `${count} ${pluralize(count, forms)}`;
}

export const WORDS = {
  module: ["модуль", "модуля", "модулей"],
  lesson: ["урок", "урока", "уроков"],
  material: ["материал", "материала", "материалов"],
  block: ["блок", "блока", "блоков"],
  item: ["элемент", "элемента", "элементов"],
};

export function getApiErrorMessage(error, fallback) {
  const validationMessage = error?.validationErrors
    ? Object.entries(error.validationErrors)
        .map(([field, message]) => `${field}: ${message}`)
        .join("; ")
    : "";
  const backendDetails =
    error?.payload?.error?.details || error?.payload?.details;
  const detailsMessage = backendDetails
    ? typeof backendDetails === "string"
      ? backendDetails
      : JSON.stringify(backendDetails)
    : "";

  return (
    validationMessage ||
    error?.userMessage ||
    error?.message ||
    detailsMessage ||
    fallback
  );
}

export function normalizeLesson(lesson, fallback = {}) {
  const contentBlocks =
    lesson?.contentBlocks ||
    lesson?.content_blocks ||
    fallback.contentBlocks ||
    [];
  const learningObjectives =
    lesson?.learningObjectives ||
    lesson?.learning_objectives ||
    fallback.learningObjectives ||
    [];
  const estimated =
    lesson?.estimatedTimeMinutes ??
    lesson?.estimated_time_minutes ??
    fallback.estimatedTimeMinutes ??
    null;
  return {
    id: lesson?.id || fallback.id,
    title: lesson?.title || fallback.title || "Урок без названия",
    description:
      lesson?.description || lesson?.summary || fallback.description || "",
    order: Number.isFinite(lesson?.order)
      ? lesson.order
      : Number.isFinite(fallback.order)
        ? fallback.order
        : 1,
    learningObjectives: Array.isArray(learningObjectives)
      ? learningObjectives
      : [],
    estimatedTimeMinutes: Number.isFinite(Number(estimated)) && estimated !== null
      ? Number(estimated)
      : null,
    contentBlocks: Array.isArray(contentBlocks) ? contentBlocks : [],
    materialIds: lesson?.materialIds || fallback.materialIds || [],
    moduleId: lesson?.moduleId ?? fallback.moduleId ?? null,
    isLocal: Boolean(lesson?.isLocal ?? fallback.isLocal),
  };
}

export function normalizeModule(module, fallback = {}) {
  const learningObjectives =
    module?.learningObjectives ||
    module?.learning_objectives ||
    fallback.learningObjectives ||
    [];
  return {
    id: module?.id || fallback.id,
    title: module?.title || fallback.title || "Модуль без названия",
    description: module?.description || fallback.description || "",
    order: Number.isFinite(module?.order)
      ? module.order
      : Number.isFinite(fallback.order)
        ? fallback.order
        : 1,
    learningObjectives: Array.isArray(learningObjectives)
      ? learningObjectives
      : [],
    lessonIds: module?.lessonIds || fallback.lessonIds || [],
  };
}

export function normalizeCourse(course, fallback = {}) {
  if (!course?.id && !fallback.id) return null;
  return {
    id: course?.id || fallback.id,
    title: course?.title || fallback.title || "",
    description: course?.description || fallback.description || "",
    difficulty:
      ["beginner", "intermediate", "advanced", "expert"].find(
        (value) => value === course?.difficulty,
      ) ||
      fallback.difficulty ||
      "beginner",
    tags: Array.isArray(course?.tags)
      ? course.tags
      : Array.isArray(fallback.tags)
        ? fallback.tags
        : [],
  };
}

/** Урок «заполнен», если у него есть контент и описание отличается от автоматического. */
export function getLessonFill(lesson) {
  const checks = [
    getLessonBlocks(lesson).length > 0,
    Boolean(lesson?.description) &&
      !/^Материалы урока \d+$/.test(lesson.description),
    (lesson?.learningObjectives || []).length > 0,
    Number.isFinite(lesson?.estimatedTimeMinutes) &&
      lesson.estimatedTimeMinutes > 0,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

export function getModuleFill(module) {
  const checks = [
    Boolean(module?.title),
    Boolean(module?.description),
    (module?.learningObjectives || []).length > 0,
    (module?.lessonIds || []).length > 0,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

export const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
