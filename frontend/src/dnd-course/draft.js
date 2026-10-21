import { getLocalStorage } from "../utils/storage";
import {
  DRAFT_KEY,
  EMPTY_COURSE_FORM,
  INTERRUPTED_UPLOAD_MESSAGE,
  LEGACY_DRAFT_KEY,
} from "./constants";
import {
  getFileKind,
  nodeId,
  normalizeCourse,
  normalizeLesson,
  normalizeModule,
} from "./helpers";

const DEFAULT_VIEWPORT = { x: 40, y: 40, zoom: 1 };

export const EMPTY_DRAFT = {
  course: null,
  courseForm: EMPTY_COURSE_FORM,
  materials: [],
  lessons: [],
  modules: [],
  positions: {},
  viewport: DEFAULT_VIEWPORT,
  selectedIds: [],
  activeNodeId: null,
  inspector: { open: false, tab: null },
  onboardingDismissed: false,
  showUsedMaterials: false,
  inspectorWidths: { normal: 440, wide: 660 },
  celebrated: false,
  filter: null,
  viewMode: null,
  forms: {},
  moduleDialog: null,
};

const PERSISTED_KEYS = Object.keys(EMPTY_DRAFT);

/** Материал без объекта File: File не сериализуется и после перезагрузки потерян. */
function restoreMaterial(material, index) {
  const status =
    material.status === "uploading"
      ? material.markdown
        ? "ready"
        : "error"
      : material.status || "error";
  return {
    id: material.id,
    fileName: material.fileName || `Материал ${index + 1}`,
    fileKind: material.fileKind || getFileKind(material.fileName),
    size: Number.isFinite(material.size) ? material.size : null,
    number: Number.isFinite(material.number) ? material.number : index + 1,
    status,
    markdown: material.markdown || "",
    proposal: material.proposal || null,
    error:
      material.status === "uploading" && !material.markdown
        ? INTERRUPTED_UPLOAD_MESSAGE
        : material.error || "",
    interrupted: material.status === "uploading" && !material.markdown,
    lessonId: material.lessonId || null,
    attachToLessonId: null,
  };
}

function sanitizeDraft(raw) {
  const draft = { ...EMPTY_DRAFT };
  for (const key of PERSISTED_KEYS) {
    if (raw[key] !== undefined && raw[key] !== null) draft[key] = raw[key];
  }
  draft.course = normalizeCourse(raw.course);
  draft.courseForm = { ...EMPTY_COURSE_FORM, ...(raw.courseForm || {}) };
  draft.materials = (Array.isArray(raw.materials) ? raw.materials : [])
    .filter((material) => material?.id)
    .map(restoreMaterial);
  draft.lessons = (Array.isArray(raw.lessons) ? raw.lessons : [])
    .filter((lesson) => lesson?.id)
    .map((lesson) => normalizeLesson(lesson));
  draft.modules = (Array.isArray(raw.modules) ? raw.modules : [])
    .filter((module) => module?.id)
    .map((module) => normalizeModule(module))
    .sort((a, b) => a.order - b.order);
  draft.positions =
    raw.positions && typeof raw.positions === "object" ? raw.positions : {};
  draft.viewport =
    raw.viewport && Number.isFinite(raw.viewport.zoom)
      ? raw.viewport
      : DEFAULT_VIEWPORT;
  draft.selectedIds = Array.isArray(raw.selectedIds) ? raw.selectedIds : [];
  draft.inspector = {
    open: Boolean(raw.inspector?.open),
    tab: raw.inspector?.tab || null,
  };
  draft.forms = raw.forms && typeof raw.forms === "object" ? raw.forms : {};
  return draft;
}

/** Старый черновик «Создать курс самостоятельно» → новая структура. */
export function migrateLegacyDraft(legacy) {
  const modules = (Array.isArray(legacy.modules) ? legacy.modules : []).map(
    (module, index) =>
      normalizeModule(module, {
        order: index + 1,
        lessonIds: module.lessonIds || [],
      }),
  );
  const moduleByLesson = new Map();
  modules.forEach((module) =>
    module.lessonIds.forEach((lessonId) =>
      moduleByLesson.set(lessonId, module.id),
    ),
  );
  const lessons = (Array.isArray(legacy.lessons) ? legacy.lessons : []).map(
    (lesson, index) =>
      normalizeLesson(lesson, {
        order: index + 1,
        materialIds: lesson.blockIds || [],
        moduleId: moduleByLesson.get(lesson.id) || null,
        // Урок без модуля сервер не даст редактировать — переносим его как черновик.
        isLocal: !moduleByLesson.get(lesson.id),
      }),
  );
  const materials = (Array.isArray(legacy.blocks) ? legacy.blocks : []).map(
    (block, index) => ({
      id: block.id,
      fileName: block.fileName || block.file?.name || "",
      size: null,
      number: block.blockNumber || index + 1,
      status: block.status,
      markdown: block.markdown || "",
      proposal: block.proposal || null,
      error: block.error || "",
      lessonId: block.lessonId || null,
    }),
  );

  let activeNodeId = null;
  if (legacy.activeLessonId) activeNodeId = nodeId.lesson(legacy.activeLessonId);
  else if (legacy.editingStructure?.type === "module")
    activeNodeId = nodeId.module(legacy.editingStructure.id);
  else if (legacy.editingStructure?.id)
    activeNodeId = nodeId.lesson(legacy.editingStructure.id);
  else if (legacy.chatBlockId || legacy.editingBlockId)
    activeNodeId = nodeId.material(legacy.chatBlockId || legacy.editingBlockId);

  return sanitizeDraft({
    course: legacy.createdCourse || null,
    courseForm: legacy.courseDraft || EMPTY_COURSE_FORM,
    materials,
    lessons,
    modules,
    positions: {},
    activeNodeId,
    inspector: {
      open: Boolean(activeNodeId),
      tab: legacy.chatBlockId ? "ai" : null,
    },
    onboardingDismissed: Boolean(legacy.createdCourse?.id),
  });
}

export function loadDraft() {
  const storage = getLocalStorage();
  if (!storage) return { draft: { ...EMPTY_DRAFT }, migrated: false };

  try {
    const current = JSON.parse(storage.getItem(DRAFT_KEY) || "null");
    if (current && typeof current === "object") {
      return { draft: sanitizeDraft(current), migrated: false };
    }
  } catch {
    // Повреждённый черновик игнорируем и пробуем старый формат.
  }

  try {
    const legacy = JSON.parse(storage.getItem(LEGACY_DRAFT_KEY) || "null");
    if (legacy && typeof legacy === "object") {
      const draft = migrateLegacyDraft(legacy);
      // Старый ключ удаляем только после того, как новый точно записан.
      if (saveDraft(draft)) storage.removeItem(LEGACY_DRAFT_KEY);
      return { draft, migrated: true };
    }
  } catch {
    // Старый черновик нечитаем — начинаем с чистого листа.
  }

  return { draft: { ...EMPTY_DRAFT }, migrated: false };
}

export function pickDraft(state) {
  const draft = {};
  for (const key of PERSISTED_KEYS) draft[key] = state[key];
  draft.materials = (state.materials || []).map(
    ({ attachToLessonId, ...material }) => material,
  );
  return draft;
}

export function saveDraft(state) {
  const storage = getLocalStorage();
  if (!storage) return false;
  try {
    storage.setItem(DRAFT_KEY, JSON.stringify({ version: 2, ...pickDraft(state) }));
    return true;
  } catch {
    return false;
  }
}

export function clearDraft({ includeLegacy = true } = {}) {
  const storage = getLocalStorage();
  try {
    storage?.removeItem(DRAFT_KEY);
    if (includeLegacy) storage?.removeItem(LEGACY_DRAFT_KEY);
  } catch {
    // ничего страшного: черновик просто останется
  }
}
