import { create } from "zustand";
import {
  createAgentConversationKey,
  useAgentStore,
} from "../stores/agentStore";
import {
  assignLessonToModule,
  createCourse as createCourseApi,
  createLesson as createLessonApi,
  createModule as createModuleApi,
  deleteLesson as deleteLessonApi,
  deleteModule as deleteModuleApi,
  getCourseBasicInfo,
  isAuthenticated,
  redirectToLogin,
  updateCourse as updateCourseApi,
  updateLesson as updateLessonApi,
  updateLessonContentBlocks,
  updateModule as updateModuleApi,
  uploadDocument,
} from "../utils/api";
import {
  COLUMN_GAP,
  COLUMN_X,
  EMPTY_COURSE_FORM,
  MAX_FILE_SIZE_BYTES,
  MAX_FILE_SIZE_LABEL,
  NODE_SIZE,
} from "./constants";
import { clearDraft, EMPTY_DRAFT, loadDraft, pickDraft, saveDraft } from "./draft";
import {
  countLabel,
  createLocalId,
  getApiErrorMessage,
  getFileKind,
  getLessonBlocks,
  MAX_CONTENT_BLOCKS,
  materialsToContentBlocks,
  nodeId,
  normalizeCourse,
  normalizeLesson,
  normalizeModule,
  objectivesToText,
  parseObjectives,
  parseTags,
  tagsToText,
  WORDS,
} from "./helpers";
import { findFreeSlot, freeRects, resolveFreePositions } from "./layout";
import { fetchCourseStructure, fetchLessonBlocks } from "./serverCourse";

// File нельзя положить в localStorage — держим их в памяти до перезагрузки.
const fileRegistry = new Map();
const contentTimers = new Map();
const contentSaves = new Map();
let toastSeq = 0;
let persistTimer = null;
let persistenceStarted = false;

const TRANSIENT = {
  hydrated: false,
  pending: {},
  saveStatus: {},
  saveErrors: {},
  courseError: "",
  courseNotice: "",
  toasts: [],
  confirm: null,
  finishOpen: false,
  finishError: "",
  materialPicker: null,
  announcement: "",
  flash: {},
  focusRequest: null,
  paletteOpen: true,
  fullscreen: false,
  dropHint: null,
  dragKind: null,
};

export function hasFile(materialId) {
  return fileRegistry.has(materialId);
}

export function formFromEntity(type, entity) {
  if (!entity) return {};
  if (type === "course") {
    return {
      title: entity.title || "",
      description: entity.description || "",
      difficulty: entity.difficulty || "beginner",
      tags: tagsToText(entity.tags),
    };
  }
  if (type === "lesson") {
    return {
      title: entity.title || "",
      description: entity.description || "",
      learningObjectives: objectivesToText(entity.learningObjectives),
      estimatedTimeMinutes:
        entity.estimatedTimeMinutes === null ||
        entity.estimatedTimeMinutes === undefined
          ? ""
          : String(entity.estimatedTimeMinutes),
    };
  }
  if (type === "module") {
    return {
      title: entity.title || "",
      description: entity.description || "",
      learningObjectives: objectivesToText(entity.learningObjectives),
    };
  }
  return {};
}

function isSameForm(a, b) {
  return Object.keys({ ...a, ...b }).every(
    (key) => String(a?.[key] ?? "") === String(b?.[key] ?? ""),
  );
}

export const useDndCourseStore = create((set, get) => {
  const patchMaterial = (id, patch) =>
    set((state) => ({
      materials: state.materials.map((material) =>
        material.id === id ? { ...material, ...patch } : material,
      ),
    }));

  const patchLesson = (id, patch) =>
    set((state) => ({
      lessons: state.lessons.map((lesson) =>
        lesson.id === id ? { ...lesson, ...patch } : lesson,
      ),
    }));

  const setPending = (key, value) =>
    set((state) => {
      const pending = { ...state.pending };
      if (value) pending[key] = true;
      else delete pending[key];
      return { pending };
    });

  const setSaveStatus = (key, status, error = "") =>
    set((state) => {
      const saveStatus = { ...state.saveStatus };
      const saveErrors = { ...state.saveErrors };
      if (status) saveStatus[key] = status;
      else delete saveStatus[key];
      if (error) saveErrors[key] = error;
      else delete saveErrors[key];
      return { saveStatus, saveErrors };
    });

  const toast = (type, text, options = {}) => {
    toastSeq += 1;
    const id = toastSeq;
    set((state) => ({
      toasts: [...state.toasts.slice(-2), { id, type, text, ...options }],
    }));
    const timeout = options.timeout ?? (type === "error" ? 7000 : 4200);
    if (timeout > 0) {
      window.setTimeout(() => get().dismissToast(id), timeout);
    }
    return id;
  };

  let announceFlip = false;
  const announce = (text) => {
    // Чередуем невидимый символ, чтобы одинаковые сообщения тоже озвучивались.
    announceFlip = !announceFlip;
    set({ announcement: announceFlip ? `${text}${String.fromCharCode(8203)}` : text });
  };

  const flashEdges = (edgeIds) => {
    const now = Date.now();
    set((state) => ({
      flash: {
        ...state.flash,
        ...Object.fromEntries(edgeIds.map((id) => [id, now])),
      },
    }));
    window.setTimeout(() => {
      set((state) => {
        const flash = { ...state.flash };
        edgeIds.forEach((id) => {
          if (flash[id] === now) delete flash[id];
        });
        return { flash };
      });
    }, 1400);
  };

  const getFormValues = (key, type, entity) =>
    get().forms[key] || formFromEntity(type, entity);

  const clearForm = (key) =>
    set((state) => {
      const forms = { ...state.forms };
      delete forms[key];
      return { forms };
    });

  const moduleOfLesson = (lessonId, modules = get().modules) =>
    modules.find((module) => (module.lessonIds || []).includes(lessonId)) ||
    null;

  const flushLessonContent = async (lessonId) => {
    const timer = contentTimers.get(lessonId);
    if (timer) {
      window.clearTimeout(timer);
      contentTimers.delete(lessonId);
      await get().saveLessonContentNow(lessonId);
    }
    const running = contentSaves.get(lessonId);
    if (running) await running.promise.catch(() => null);
  };

  const sendOrderUpdates = (items, updater) =>
    Promise.allSettled(items.map((item) => updater(item)));

  // Урок без модуля живёт только в черновике: сервер проверяет права на урок
  // через его модуль, поэтому урок без модуля нельзя ни изменить, ни удалить.
  // На сервер урок уходит в момент добавления в модуль — сразу с module_id.
  const materializeLesson = async (lessonId, moduleId, order) => {
    const lesson = get().lessons.find((item) => item.id === lessonId);
    if (!lesson) throw new Error("Урок не найден.");
    const saved = await createLessonApi({
      title: lesson.title,
      description: lesson.description || lesson.title,
      order,
      learningObjectives: lesson.learningObjectives || [],
      estimatedTimeMinutes: lesson.estimatedTimeMinutes ?? null,
      moduleId,
    });
    if (!saved?.id) throw new Error("Сервер не вернул идентификатор урока.");
    const blocks = getLessonBlocks(lesson);
    if (blocks.length) {
      try {
        await updateLessonContentBlocks(saved.id, blocks);
      } catch (error) {
        let rollbackFailed = false;
        try {
          await deleteLessonApi(saved.id);
        } catch {
          rollbackFailed = true;
        }
        throw Object.assign(error instanceof Error ? error : new Error(String(error)), {
          rollbackFailed,
        });
      }
    }
    return saved.id;
  };

  const remapLessonId = (oldId, newId, patch = {}) => {
    const oldKey = nodeId.lesson(oldId);
    const newKey = nodeId.lesson(newId);
    const rekey = (source) => {
      const next = {};
      Object.entries(source || {}).forEach(([key, value]) => {
        next[key.startsWith(oldKey) ? newKey + key.slice(oldKey.length) : key] = value;
      });
      return next;
    };
    set((state) => ({
      lessons: state.lessons.map((lesson) =>
        lesson.id === oldId ? { ...lesson, ...patch, id: newId, isLocal: false } : lesson,
      ),
      materials: state.materials.map((material) =>
        material.lessonId === oldId ? { ...material, lessonId: newId } : material,
      ),
      modules: state.modules.map((module) =>
        module.lessonIds.includes(oldId)
          ? { ...module, lessonIds: module.lessonIds.map((id) => (id === oldId ? newId : id)) }
          : module,
      ),
      positions: rekey(state.positions),
      forms: rekey(state.forms),
      saveStatus: rekey(state.saveStatus),
      saveErrors: rekey(state.saveErrors),
      selectedIds: state.selectedIds.map((id) => (id === oldKey ? newKey : id)),
      activeNodeId: state.activeNodeId === oldKey ? newKey : state.activeNodeId,
    }));
  };

  const rollbackNote = (error) =>
    error?.rollbackFailed
      ? " Откат выполнен не полностью: пустой урок мог остаться на сервере."
      : " Изменения отменены.";

  return {
    ...EMPTY_DRAFT,
    ...TRANSIENT,

    hydrate: () => {
      if (get().hydrated) return;
      const { draft, migrated } = loadDraft();
      set({ ...draft, hydrated: true });
      get().verifyCourse();
      if (migrated) {
        toast(
          "info",
          "Черновик из старого конструктора перенесён на холст. Позиции элементов расставлены автоматически.",
        );
      }
      if (!persistenceStarted) {
        persistenceStarted = true;
        useDndCourseStore.subscribe((state, previous) => {
          if (!state.hydrated) return;
          const changed = Object.keys(EMPTY_DRAFT).some(
            (key) => state[key] !== previous[key],
          );
          if (!changed) return;
          window.clearTimeout(persistTimer);
          persistTimer = window.setTimeout(() => get().persistNow(), 450);
        });
        window.addEventListener("beforeunload", () => get().persistNow());
      }
    },

    persistNow: () => {
      window.clearTimeout(persistTimer);
      const state = get();
      if (!state.hydrated) return;
      const isEmpty =
        !state.course &&
        !state.materials.length &&
        !state.courseForm.title &&
        !state.courseForm.description;
      if (isEmpty) clearDraft({ includeLegacy: false });
      else saveDraft(pickDraft(state));
    },

    dismissToast: (id) =>
      set((state) => ({ toasts: state.toasts.filter((item) => item.id !== id) })),
    toast,
    announce,

    // ───────────── Курс ─────────────
    // Черновик живёт в браузере дольше базы: если курс на сервере пропал
    // (например, базу пересоздали), работать с ним нельзя — все запросы упадут.
    verifyCourse: async () => {
      const courseId = get().course?.id;
      if (!courseId) return;
      try {
        await getCourseBasicInfo(courseId);
      } catch (error) {
        if (error?.status !== 404 && error?.status !== 400) return;
        if (get().course?.id !== courseId) return;
        set((state) => {
          const stale = state.course;
          const removedLessons = new Set(
            state.lessons.filter((lesson) => !lesson.isLocal).map((lesson) => lesson.id),
          );
          const positions = Object.fromEntries(
            Object.entries(state.positions).filter(
              ([key]) =>
                !key.startsWith("module:") &&
                !(key.startsWith("lesson:") && removedLessons.has(key.slice("lesson:".length))),
            ),
          );
          return {
            course: null,
            courseForm: {
              title: stale.title || "",
              description: stale.description || "",
              difficulty: stale.difficulty || "beginner",
              tags: tagsToText(stale.tags),
            },
            lessons: state.lessons.filter((lesson) => lesson.isLocal),
            modules: [],
            materials: state.materials.map((material) =>
              removedLessons.has(material.lessonId) ? { ...material, lessonId: null } : material,
            ),
            positions,
            selectedIds: [],
            activeNodeId: null,
            inspector: { open: false, tab: null },
            forms: {},
            moduleDialog: null,
            finishOpen: false,
            courseNotice:
              "Курс из черновика не найден на сервере — похоже, база была очищена. Загруженные материалы сохранились: создайте курс заново, и они вернутся на холст.",
          };
        });
      }
    },

    setCourseForm: (patch) =>
      set((state) => ({
        courseForm: { ...state.courseForm, ...patch },
        courseError: "",
      })),

    createCourse: async () => {
      const { courseForm, pending, course } = get();
      if (pending.course || course?.id) return;
      const title = courseForm.title.trim();
      const description = courseForm.description.trim();
      if (!title || !description) {
        set({ courseError: "Заполните название и описание курса." });
        return;
      }
      const tags = parseTags(courseForm.tags);
      setPending("course", true);
      set({ courseError: "" });
      try {
        const created = await createCourseApi({
          title,
          description,
          difficulty: courseForm.difficulty || "beginner",
          tags,
        });
        const nextCourse = normalizeCourse(created, {
          title,
          description,
          difficulty: courseForm.difficulty,
          tags,
        });
        if (!nextCourse?.id) throw new Error("Сервер не вернул идентификатор курса.");
        set({
          course: nextCourse,
          courseNotice: "",
          courseForm: EMPTY_COURSE_FORM,
          onboardingDismissed: false,
          activeNodeId: null,
          inspector: { open: false, tab: null },
          selectedIds: [],
          focusRequest: { ids: ["course", "upload"], at: Date.now() },
        });
        announce("Курс создан. Открыт конструктор.");
      } catch (error) {
        set({
          courseError: getApiErrorMessage(
            error,
            "Не удалось создать курс. Проверьте соединение и попробуйте ещё раз.",
          ),
        });
      } finally {
        setPending("course", false);
      }
    },

    saveCourse: async () => {
      const { course, pending } = get();
      if (!course?.id || pending.course) return;
      const values = getFormValues("course", "course", course);
      const title = values.title.trim();
      const description = values.description.trim();
      if (!title || !description) {
        setSaveStatus("course", "error", "Заполните название и описание курса.");
        return;
      }
      const tags = parseTags(values.tags);
      setPending("course", true);
      setSaveStatus("course", "saving");
      try {
        const updated = await updateCourseApi(course.id, {
          title,
          description,
          difficulty: values.difficulty,
          tags,
        });
        set({
          course: normalizeCourse(
            { ...(updated || {}), id: course.id },
            { title, description, difficulty: values.difficulty, tags },
          ),
        });
        set((state) => ({
          course: {
            ...state.course,
            title,
            description,
            difficulty: values.difficulty,
            tags,
          },
        }));
        clearForm("course");
        setSaveStatus("course", "saved");
        toast("success", "Карточка курса сохранена");
      } catch (error) {
        setSaveStatus(
          "course",
          "error",
          getApiErrorMessage(error, "Не удалось сохранить курс."),
        );
      } finally {
        setPending("course", false);
      }
    },

    // ───────────── Материалы ─────────────
    addFiles: (fileList, { position = null, attachToLessonId = null } = {}) => {
      const state = get();
      if (!state.course?.id) return [];
      const picked = Array.from(fileList || []);
      if (!picked.length) return [];

      const startNumber =
        state.materials.reduce((max, item) => Math.max(max, item.number || 0), 0) + 1;
      const rects = freeRects(state);
      const positions = {};
      const created = picked.map((file, index) => {
        const id = createLocalId("material");
        const tooBig = file.size > MAX_FILE_SIZE_BYTES;
        if (!tooBig) fileRegistry.set(id, file);
        const desired = position
          ? {
              x: position.x,
              y: position.y + index * (NODE_SIZE.material.height + COLUMN_GAP),
            }
          : { x: COLUMN_X.material, y: NODE_SIZE.upload.height + COLUMN_GAP };
        const slot = position
          ? desired
          : findFreeSlot(desired, NODE_SIZE.material, rects);
        rects.push({ ...slot, ...NODE_SIZE.material });
        positions[nodeId.material(id)] = slot;
        return {
          id,
          fileName: file.name,
          fileKind: getFileKind(file.name),
          size: file.size,
          number: startNumber + index,
          status: tooBig ? "error" : "uploading",
          markdown: "",
          proposal: null,
          error: tooBig
            ? `Файл больше ${MAX_FILE_SIZE_LABEL} и не был отправлен. Максимальный размер — ${MAX_FILE_SIZE_LABEL}.`
            : "",
          tooBig,
          interrupted: false,
          lessonId: null,
          attachToLessonId: tooBig ? null : attachToLessonId,
        };
      });

      set((current) => ({
        materials: [...current.materials, ...created],
        positions: { ...current.positions, ...positions },
        focusRequest: {
          ids: created.map((material) => nodeId.material(material.id)),
          at: Date.now(),
        },
      }));

      const rejected = created.filter((material) => material.tooBig);
      if (rejected.length) {
        toast(
          "warning",
          rejected.length === 1
            ? `«${rejected[0].fileName}» больше ${MAX_FILE_SIZE_LABEL} — файл не отправлен. Остальные материалы обрабатываются.`
            : `${countLabel(rejected.length, ["файл", "файла", "файлов"])} больше ${MAX_FILE_SIZE_LABEL} — не отправлены.`,
        );
      }
      announce(
        `Добавлено ${countLabel(created.length, WORDS.material)}. Обрабатываем документы.`,
      );
      created
        .filter((material) => material.status === "uploading")
        .forEach((material) => get().uploadMaterial(material.id));
      return created.map((material) => material.id);
    },

    uploadMaterial: async (id) => {
      const file = fileRegistry.get(id);
      const material = get().materials.find((item) => item.id === id);
      if (!file || !material || get().pending[nodeId.material(id)]) return;
      if (!isAuthenticated()) {
        redirectToLogin();
        return;
      }
      const key = nodeId.material(id);
      setPending(key, true);
      patchMaterial(id, { status: "uploading", error: "", interrupted: false });
      try {
        const markdown = await uploadDocument(file);
        patchMaterial(id, {
          status: "ready",
          markdown: typeof markdown === "string" ? markdown : String(markdown || ""),
          error: "",
        });
        setPending(key, false);
        announce(`Материал «${material.fileName}» готов.`);
        const stillUploading = get().materials.some(
          (item) => item.status === "uploading",
        );
        if (!stillUploading) toast("success", "Материал обработан");
        const target = get().materials.find((item) => item.id === id)?.attachToLessonId;
        if (target) {
          patchMaterial(id, { attachToLessonId: null });
          if (get().lessons.some((lesson) => lesson.id === target)) {
            await get().addMaterialsToLesson(target, [id]);
          }
        }
      } catch (error) {
        setPending(key, false);
        const message = getApiErrorMessage(error, "Не удалось обработать документ.");
        patchMaterial(id, { status: "error", error: message, attachToLessonId: null });
        toast("error", `Не удалось обработать документ «${material.fileName}»`);
        announce(`Ошибка: не удалось обработать «${material.fileName}».`);
      }
    },

    retryMaterial: (id, replacementFile = null) => {
      const material = get().materials.find((item) => item.id === id);
      if (!material) return false;
      if (replacementFile) {
        if (replacementFile.size > MAX_FILE_SIZE_BYTES) {
          patchMaterial(id, {
            fileName: replacementFile.name,
            fileKind: getFileKind(replacementFile.name),
            size: replacementFile.size,
            status: "error",
            tooBig: true,
            error: `Файл больше ${MAX_FILE_SIZE_LABEL} и не был отправлен. Максимальный размер — ${MAX_FILE_SIZE_LABEL}.`,
          });
          return true;
        }
        fileRegistry.set(id, replacementFile);
        patchMaterial(id, {
          fileName: replacementFile.name,
          fileKind: getFileKind(replacementFile.name),
          size: replacementFile.size,
          tooBig: false,
        });
      }
      if (!fileRegistry.has(id)) return false;
      get().uploadMaterial(id);
      return true;
    },

    updateMaterialMarkdown: (id, markdown) => patchMaterial(id, { markdown }),

    deleteMaterial: (id) => {
      const material = get().materials.find((item) => item.id === id);
      if (!material || material.lessonId) return;
      fileRegistry.delete(id);
      const key = nodeId.material(id);
      set((state) => {
        const positions = { ...state.positions };
        delete positions[key];
        return {
          materials: state.materials.filter((item) => item.id !== id),
          positions,
          selectedIds: state.selectedIds.filter((item) => item !== key),
          activeNodeId: state.activeNodeId === key ? null : state.activeNodeId,
          inspector:
            state.activeNodeId === key
              ? { open: false, tab: null }
              : state.inspector,
        };
      });
      toast("success", "Материал удалён");
    },

    askMaterialAi: async (id, prompt) => {
      const { course, materials } = get();
      const material = materials.find((item) => item.id === id);
      const text = String(prompt || "").trim();
      if (!course?.id || !material || !text) return;
      const key = createAgentConversationKey("editor", course.id, `manual:${id}`);
      if (useAgentStore.getState().conversations[key]?.status === "loading") return;
      patchMaterial(id, { aiError: "" });
      try {
        const response = await useAgentStore.getState().sendMessage({
          key,
          agent: "editor",
          courseId: course.id,
          content: text,
          contentBlocks: materialsToContentBlocks(
            materials.filter((item) => item.id !== id && !item.lessonId),
          ),
          editorPayload: {
            content_type: "text",
            content_block: JSON.stringify({
              content_type: "text",
              ai_generated: false,
              md_content: material.markdown || "",
            }),
            images: undefined,
          },
          emptyResponseMessage: "",
          responseDisplayMessage: (agentResponse) =>
            typeof agentResponse?.parsedContent?.md_content === "string" &&
            agentResponse.parsedContent.md_content.trim()
              ? "Правка готова. Проверьте предложенный вариант и примените его, если он подходит."
              : "",
        });
        if (!response) return;
        const proposal = response.parsedContent?.md_content;
        if (typeof proposal !== "string" || !proposal.trim()) {
          patchMaterial(id, {
            aiError:
              "ИИ вернул ответ в неподдерживаемом формате. Попробуйте уточнить запрос.",
          });
          return;
        }
        patchMaterial(id, { proposal: proposal.trim() });
        announce("ИИ подготовил правку материала.");
      } catch {
        // Ошибку сети уже записал agent store — инспектор покажет её с кнопкой «Повторить».
      }
    },

    applyProposal: (id) => {
      const material = get().materials.find((item) => item.id === id);
      if (!material?.proposal) return;
      patchMaterial(id, { markdown: material.proposal, proposal: null });
      toast("success", "Правка применена");
    },

    rejectProposal: (id) => patchMaterial(id, { proposal: null }),

    // ───────────── Уроки ─────────────
    validateMaterialsForLesson: (materialIds, lessonId = null) => {
      const { materials, lessons } = get();
      const picked = materialIds
        .map((id) => materials.find((item) => item.id === id))
        .filter(Boolean);
      if (!picked.length) return { ok: false, reason: "Выберите готовые материалы." };
      if (picked.some((item) => item.status === "uploading"))
        return { ok: false, reason: "Материал ещё обрабатывается." };
      if (picked.some((item) => item.status === "error"))
        return { ok: false, reason: "Материал с ошибкой нельзя добавить в урок." };
      if (picked.some((item) => item.lessonId))
        return { ok: false, reason: "Материал уже добавлен в урок." };
      if (!materialsToContentBlocks(picked).length)
        return { ok: false, reason: "В материале нет текста." };
      const existing = lessonId
        ? getLessonBlocks(lessons.find((lesson) => lesson.id === lessonId)).length
        : 0;
      if (existing + picked.length > MAX_CONTENT_BLOCKS) {
        return {
          ok: false,
          reason: `В уроке может быть не больше ${MAX_CONTENT_BLOCKS} блоков.`,
        };
      }
      return { ok: true, materials: picked };
    },

    createLessonFromMaterials: async (materialIds, { position = null } = {}) => {
      const state = get();
      if (!state.course?.id) return null;
      const check = state.validateMaterialsForLesson(materialIds);
      if (!check.ok) {
        toast("warning", check.reason);
        return null;
      }
      const picked = check.materials;
      const lessonNumber = state.lessons.length + 1;
      const lesson = {
        id: createLocalId("lesson"),
        title: `Урок ${lessonNumber}`,
        description: `Материалы урока ${lessonNumber}`,
        order: lessonNumber,
        learningObjectives: [],
        estimatedTimeMinutes: null,
        contentBlocks: materialsToContentBlocks(picked),
        materialIds: picked.map((item) => item.id),
        moduleId: null,
        isLocal: true,
      };

      const resolved = resolveFreePositions(state);
      const materialPositions = picked
        .map((item) => resolved[nodeId.material(item.id)])
        .filter(Boolean);
      const desired = position || {
        x: Math.max(
          COLUMN_X.lesson,
          ...materialPositions.map((point) => point.x + NODE_SIZE.material.width + 60),
        ),
        y: materialPositions.length
          ? materialPositions.reduce((sum, point) => sum + point.y, 0) / materialPositions.length
          : 0,
      };
      const slot = findFreeSlot(desired, NODE_SIZE.lesson, freeRects(state));
      const lessonNode = nodeId.lesson(lesson.id);
      set((current) => ({
        lessons: [...current.lessons, lesson],
        materials: current.materials.map((item) =>
          lesson.materialIds.includes(item.id) ? { ...item, lessonId: lesson.id } : item,
        ),
        positions: { ...current.positions, [lessonNode]: slot },
        selectedIds: [lessonNode],
        activeNodeId: lessonNode,
        inspector: { open: true, tab: "main" },
      }));
      flashEdges(lesson.materialIds.map((id) => `edge:${nodeId.material(id)}->${lessonNode}`));
      toast("success", "Урок создан. На сервер он попадёт вместе с модулем.");
      announce(`${lesson.title} создан из ${countLabel(picked.length, WORDS.material)}.`);
      return lesson.id;
    },

    addMaterialsToLesson: async (lessonId, materialIds) => {
      const key = nodeId.lesson(lessonId);
      if (get().pending[key]) {
        toast("warning", "Урок ещё сохраняется. Попробуйте через секунду.");
        return false;
      }
      await flushLessonContent(lessonId);
      const check = get().validateMaterialsForLesson(materialIds, lessonId);
      if (!check.ok) {
        toast("warning", check.reason);
        return false;
      }
      const lesson = get().lessons.find((item) => item.id === lessonId);
      if (!lesson) return false;
      const picked = check.materials;
      const nextBlocks = [...getLessonBlocks(lesson), ...materialsToContentBlocks(picked)];
      const ids = picked.map((item) => item.id);
      const applyLocally = () =>
        set((state) => ({
          lessons: state.lessons.map((item) =>
            item.id === lessonId
              ? { ...item, contentBlocks: nextBlocks, materialIds: [...(item.materialIds || []), ...ids] }
              : item,
          ),
          materials: state.materials.map((item) =>
            ids.includes(item.id) ? { ...item, lessonId } : item,
          ),
        }));
      if (lesson.isLocal) {
        applyLocally();
        flashEdges(ids.map((id) => `edge:${nodeId.material(id)}->${key}`));
        toast("success", picked.length === 1 ? "Материал добавлен в урок" : "Материалы добавлены в урок");
        return true;
      }
      setPending(key, true);
      picked.forEach((item) => setPending(nodeId.material(item.id), true));
      try {
        await updateLessonContentBlocks(lessonId, nextBlocks);
        applyLocally();
        flashEdges(ids.map((id) => `edge:${nodeId.material(id)}->${key}`));
        toast(
          "success",
          picked.length === 1 ? "Материал добавлен в урок" : "Материалы добавлены в урок",
        );
        announce(`Добавлено в «${lesson.title}»: ${countLabel(picked.length, WORDS.material)}.`);
        return true;
      } catch (error) {
        toast("error", getApiErrorMessage(error, "Не удалось добавить материал в урок."), {
          retry: () => get().addMaterialsToLesson(lessonId, materialIds),
        });
        return false;
      } finally {
        setPending(key, false);
        picked.forEach((item) => setPending(nodeId.material(item.id), false));
      }
    },

    saveLessonMeta: async (lessonId) => {
      const { course, lessons, pending } = get();
      const lesson = lessons.find((item) => item.id === lessonId);
      const key = nodeId.lesson(lessonId);
      if (!course?.id || !lesson || pending[key]) return;
      const values = getFormValues(key, "lesson", lesson);
      const title = values.title.trim();
      const description = values.description.trim();
      if (!title || !description) {
        setSaveStatus(key, "error", "Заполните название и описание урока.");
        return;
      }
      const learningObjectives = parseObjectives(values.learningObjectives);
      const minutes = values.estimatedTimeMinutes === "" ? null : Number(values.estimatedTimeMinutes);
      const estimatedTimeMinutes =
        Number.isFinite(minutes) && minutes > 0 ? Math.round(minutes) : null;
      if (lesson.isLocal) {
        patchLesson(lessonId, { title, description, learningObjectives, estimatedTimeMinutes });
        clearForm(key);
        setSaveStatus(key, "saved");
        return;
      }
      setPending(key, true);
      setSaveStatus(key, "saving");
      try {
        await updateLessonApi(course.id, lessonId, {
          title,
          description,
          learningObjectives,
          estimatedTimeMinutes,
        });
        patchLesson(lessonId, { title, description, learningObjectives, estimatedTimeMinutes });
        clearForm(key);
        setSaveStatus(key, "saved");
      } catch (error) {
        setSaveStatus(key, "error", getApiErrorMessage(error, "Не удалось сохранить урок."));
      } finally {
        setPending(key, false);
      }
    },

    setLessonContent: (lessonId, contentBlocks) => {
      patchLesson(lessonId, { contentBlocks });
      const statusKey = `${nodeId.lesson(lessonId)}:content`;
      if (get().lessons.find((item) => item.id === lessonId)?.isLocal) {
        setSaveStatus(statusKey, "saved");
        return;
      }
      setSaveStatus(statusKey, "dirty");
      window.clearTimeout(contentTimers.get(lessonId));
      contentTimers.set(
        lessonId,
        window.setTimeout(() => {
          contentTimers.delete(lessonId);
          get().saveLessonContentNow(lessonId);
        }, 700),
      );
    },

    saveLessonContentNow: async (lessonId) => {
      const statusKey = `${nodeId.lesson(lessonId)}:content`;
      const running = contentSaves.get(lessonId);
      if (running) {
        running.again = true;
        return running.promise;
      }
      const entry = { again: false, promise: null };
      entry.promise = (async () => {
        do {
          entry.again = false;
          const lesson = get().lessons.find((item) => item.id === lessonId);
          if (!lesson || lesson.isLocal) return;
          setSaveStatus(statusKey, "saving");
          try {
            await updateLessonContentBlocks(lessonId, getLessonBlocks(lesson));
            setSaveStatus(statusKey, entry.again ? "saving" : "saved");
          } catch (error) {
            setSaveStatus(
              statusKey,
              "error",
              getApiErrorMessage(error, "Не удалось сохранить контент урока."),
            );
            return;
          }
        } while (entry.again);
      })();
      contentSaves.set(lessonId, entry);
      try {
        await entry.promise;
      } finally {
        contentSaves.delete(lessonId);
      }
      return undefined;
    },

    deleteLesson: async (lessonId) => {
      const { lessons, modules, course } = get();
      const lesson = lessons.find((item) => item.id === lessonId);
      const key = nodeId.lesson(lessonId);
      if (!lesson || get().pending[key]) return false;
      window.clearTimeout(contentTimers.get(lessonId));
      contentTimers.delete(lessonId);
      setPending(key, true);
      try {
        if (!lesson.isLocal) await deleteLessonApi(lessonId);
        const parent = moduleOfLesson(lessonId, modules);
        const remaining = parent
          ? parent.lessonIds.filter((id) => id !== lessonId)
          : [];
        set((state) => {
          const positions = { ...state.positions };
          delete positions[key];
          const forms = { ...state.forms };
          delete forms[key];
          return {
            lessons: state.lessons
              .filter((item) => item.id !== lessonId)
              .map((item) =>
                remaining.includes(item.id)
                  ? { ...item, order: remaining.indexOf(item.id) + 1 }
                  : item,
              ),
            modules: state.modules.map((module) =>
              module.id === parent?.id ? { ...module, lessonIds: remaining } : module,
            ),
            materials: state.materials.map((item) =>
              item.lessonId === lessonId ? { ...item, lessonId: null } : item,
            ),
            positions,
            forms,
            selectedIds: state.selectedIds.filter((id) => id !== key),
            activeNodeId: state.activeNodeId === key ? null : state.activeNodeId,
            inspector:
              state.activeNodeId === key ? { open: false, tab: null } : state.inspector,
          };
        });
        if (parent && remaining.length && course?.id) {
          sendOrderUpdates(remaining, (id) =>
            updateLessonApi(course.id, id, { order: remaining.indexOf(id) + 1 }),
          );
        }
        toast("success", "Урок удалён");
        announce(`Урок «${lesson.title}» удалён. Его материалы снова свободны.`);
        return true;
      } catch (error) {
        toast("error", getApiErrorMessage(error, "Не удалось удалить урок."));
        return false;
      } finally {
        setPending(key, false);
      }
    },

    // ───────────── Модули ─────────────
    openModuleDialog: (lessonIds = [], { pick = false } = {}) => {
      const { modules } = get();
      set({
        moduleDialog: {
          title: `Модуль ${modules.length + 1}`,
          description: "",
          learningObjectives: "",
          lessonIds,
          pick,
          error: "",
        },
      });
    },

    updateModuleDialog: (patch) =>
      set((state) =>
        state.moduleDialog
          ? { moduleDialog: { ...state.moduleDialog, ...patch, error: "" } }
          : {},
      ),

    closeModuleDialog: () => {
      if (get().pending["create-module"]) return;
      set({ moduleDialog: null });
    },

    submitModuleDialog: async () => {
      const { moduleDialog, course, modules, lessons, pending } = get();
      if (!moduleDialog || !course?.id || pending["create-module"]) return;
      const title = moduleDialog.title.trim();
      const description = moduleDialog.description.trim();
      const lessonIds = moduleDialog.lessonIds.filter((id) =>
        lessons.some((lesson) => lesson.id === id),
      );
      if (!title || !description) {
        set({ moduleDialog: { ...moduleDialog, error: "Заполните название и описание модуля." } });
        return;
      }
      if (!lessonIds.length) {
        set({ moduleDialog: { ...moduleDialog, error: "Выберите хотя бы один урок для модуля." } });
        return;
      }
      const learningObjectives = parseObjectives(moduleDialog.learningObjectives);
      const order = modules.length + 1;
      setPending("create-module", true);
      lessonIds.forEach((id) => setPending(nodeId.lesson(id), true));

      let savedModule = null;
      const moved = [];
      let failure = null;
      try {
        savedModule = await createModuleApi(course.id, {
          title,
          description,
          order,
          learningObjectives,
        });
        if (!savedModule?.id || savedModule.id === course.id) {
          throw new Error("Сервер не вернул корректный идентификатор модуля.");
        }
        for (const lessonId of lessonIds) {
          const lesson = get().lessons.find((item) => item.id === lessonId);
          if (lesson?.isLocal) {
            const newId = await materializeLesson(lessonId, savedModule.id, moved.length + 1);
            remapLessonId(lessonId, newId, { moduleId: savedModule.id });
            moved.push(newId);
          } else {
            await assignLessonToModule(lessonId, savedModule.id);
            moved.push(lessonId);
          }
        }
      } catch (error) {
        failure = error;
      }

      if (!savedModule?.id || (failure && !moved.length)) {
        // Пустой модуль удалять безопасно: в нём ещё нет уроков.
        let rollbackFailed = false;
        if (savedModule?.id) {
          try {
            await deleteModuleApi(savedModule.id);
          } catch {
            rollbackFailed = true;
          }
        }
        setPending("create-module", false);
        lessonIds.forEach((id) => setPending(nodeId.lesson(id), false));
        const message = getApiErrorMessage(failure, "Не удалось создать модуль.");
        set((state) => ({
          moduleDialog: state.moduleDialog
            ? {
                ...state.moduleDialog,
                error: rollbackFailed
                  ? `${message} Откат выполнен не полностью: пустой модуль мог остаться на сервере.`
                  : `${message} Изменения отменены.`,
              }
            : null,
        }));
        return;
      }

      const module = normalizeModule(savedModule, {
        title,
        description,
        order,
        learningObjectives,
      });
      module.title = title;
      module.description = description;
      module.order = order;
      module.learningObjectives = learningObjectives;
      module.lessonIds = moved;

      set((state) => {
        const positions = { ...state.positions };
        moved.forEach((id) => delete positions[nodeId.lesson(id)]);
        return {
          modules: [
            ...state.modules.map((item) => ({
              ...item,
              lessonIds: item.lessonIds.filter((id) => !moved.includes(id)),
            })),
            module,
          ],
          lessons: state.lessons.map((lesson) =>
            moved.includes(lesson.id)
              ? { ...lesson, moduleId: module.id, order: moved.indexOf(lesson.id) + 1 }
              : lesson,
          ),
          positions,
          moduleDialog: failure ? state.moduleDialog : null,
          selectedIds: [nodeId.module(module.id)],
          activeNodeId: nodeId.module(module.id),
          inspector: { open: true, tab: "main" },
        };
      });

      const orderResults = await sendOrderUpdates(moved, (id) =>
        updateLessonApi(course.id, id, { order: moved.indexOf(id) + 1 }),
      );
      setPending("create-module", false);
      lessonIds.forEach((id) => setPending(nodeId.lesson(id), false));
      flashEdges([`edge:${nodeId.module(module.id)}->course`]);

      if (failure) {
        const message = `Модуль создан, но перенесены не все уроки (${moved.length} из ${lessonIds.length}). ${getApiErrorMessage(failure, "")}`.trim();
        set((state) => ({
          moduleDialog: state.moduleDialog
            ? {
                ...state.moduleDialog,
                lessonIds: lessonIds.filter((id) => !moved.includes(id)),
                error: message,
              }
            : null,
        }));
        toast("warning", message);
        return;
      }
      if (orderResults.some((result) => result.status === "rejected")) {
        toast("warning", "Модуль создан, но порядок уроков сохранился не полностью.");
      } else {
        toast("success", "Модуль сохранён");
      }
      announce(`Модуль «${title}» создан, в нём ${countLabel(moved.length, WORDS.lesson)}.`);
    },

    moveLessonToModule: async (lessonId, targetModuleId, toIndex = null) => {
      const { course, modules, lessons, pending } = get();
      const lesson = lessons.find((item) => item.id === lessonId);
      const target = modules.find((item) => item.id === targetModuleId);
      const lessonKey = nodeId.lesson(lessonId);
      if (!course?.id || !lesson || !target) return false;
      const source = moduleOfLesson(lessonId, modules);
      if (source?.id === target.id) {
        return get().reorderLesson(target.id, lessonId, toIndex ?? target.lessonIds.length - 1);
      }
      if (pending[lessonKey] || pending[`order:${target.id}`] || (source && pending[`order:${source.id}`])) {
        toast("warning", "Предыдущее перемещение ещё сохраняется.");
        return false;
      }

      if (lesson.isLocal) {
        const insertAt =
          toIndex === null
            ? target.lessonIds.length
            : Math.max(0, Math.min(toIndex, target.lessonIds.length));
        setPending(lessonKey, true);
        setPending(`order:${target.id}`, true);
        try {
          const newId = await materializeLesson(lessonId, target.id, insertAt + 1);
          remapLessonId(lessonId, newId, { moduleId: target.id });
          const freshTarget = get().modules.find((item) => item.id === target.id);
          const targetIds = [...(freshTarget?.lessonIds || [])];
          targetIds.splice(insertAt, 0, newId);
          set((state) => {
            const positions = { ...state.positions };
            delete positions[nodeId.lesson(newId)];
            return {
              positions,
              modules: state.modules.map((item) =>
                item.id === target.id ? { ...item, lessonIds: targetIds } : item,
              ),
              lessons: state.lessons.map((item) =>
                targetIds.includes(item.id)
                  ? { ...item, order: targetIds.indexOf(item.id) + 1, moduleId: target.id }
                  : item,
              ),
            };
          });
          const following = targetIds.slice(insertAt + 1);
          const results = await sendOrderUpdates(following, (id) =>
            updateLessonApi(course.id, id, { order: targetIds.indexOf(id) + 1 }),
          );
          flashEdges([`edge:${nodeId.module(target.id)}->course`]);
          if (results.some((result) => result.status === "rejected")) {
            toast("warning", "Урок сохранён в модуле, но порядок остальных уроков обновился не полностью.");
          } else {
            toast("success", `Урок перемещён в модуль «${target.title}»`);
          }
          announce(`«${lesson.title}» сохранён в модуле «${target.title}», позиция ${insertAt + 1}.`);
          return true;
        } catch (error) {
          toast(
            "error",
            `${getApiErrorMessage(error, "Не удалось сохранить урок в модуле.")}${rollbackNote(error)}`,
            { retry: () => get().moveLessonToModule(lessonId, targetModuleId, toIndex) },
          );
          return false;
        } finally {
          setPending(lessonKey, false);
          setPending(`order:${target.id}`, false);
        }
      }

      const previous = { modules, lessons, positions: get().positions };
      const targetIds = [...target.lessonIds];
      const index = toIndex === null ? targetIds.length : Math.max(0, Math.min(toIndex, targetIds.length));
      targetIds.splice(index, 0, lessonId);
      const sourceIds = source ? source.lessonIds.filter((id) => id !== lessonId) : [];

      setPending(lessonKey, true);
      setPending(`order:${target.id}`, true);
      if (source) setPending(`order:${source.id}`, true);
      set((state) => {
        const positions = { ...state.positions };
        delete positions[lessonKey];
        return {
          modules: state.modules.map((item) => {
            if (item.id === target.id) return { ...item, lessonIds: targetIds };
            if (item.id === source?.id) return { ...item, lessonIds: sourceIds };
            return item;
          }),
          lessons: state.lessons.map((item) => {
            if (targetIds.includes(item.id))
              return { ...item, order: targetIds.indexOf(item.id) + 1, moduleId: target.id };
            if (sourceIds.includes(item.id)) return { ...item, order: sourceIds.indexOf(item.id) + 1 };
            return item;
          }),
          positions,
        };
      });

      const release = () => {
        setPending(lessonKey, false);
        setPending(`order:${target.id}`, false);
        if (source) setPending(`order:${source.id}`, false);
      };

      try {
        await assignLessonToModule(lessonId, target.id);
      } catch (error) {
        set(previous);
        release();
        toast(
          "error",
          `${getApiErrorMessage(error, "Не удалось перенести урок.")} Предыдущее состояние восстановлено.`,
        );
        return false;
      }

      const results = await sendOrderUpdates(
        [
          ...targetIds.map((id, i) => ({ id, order: i + 1 })),
          ...sourceIds.map((id, i) => ({ id, order: i + 1 })),
        ],
        (item) => updateLessonApi(course.id, item.id, { order: item.order }),
      );
      release();
      flashEdges([`edge:${nodeId.module(target.id)}->course`]);
      if (results.some((result) => result.status === "rejected")) {
        toast("warning", "Урок перенесён, но порядок уроков сохранился не полностью.");
      } else {
        toast("success", `Урок перемещён в модуль «${target.title}»`);
      }
      announce(`«${lesson.title}» перемещён в модуль «${target.title}», позиция ${index + 1}.`);
      return true;
    },

    reorderLesson: async (moduleId, lessonId, toIndex) => {
      const { course, modules, lessons, pending } = get();
      const module = modules.find((item) => item.id === moduleId);
      if (!course?.id || !module) return false;
      const lockKey = `order:${moduleId}`;
      if (pending[lockKey]) {
        toast("warning", "Порядок ещё сохраняется.");
        return false;
      }
      const ids = [...module.lessonIds];
      const from = ids.indexOf(lessonId);
      const to = Math.max(0, Math.min(toIndex, ids.length - 1));
      if (from < 0 || from === to) return false;
      ids.splice(from, 1);
      ids.splice(to, 0, lessonId);
      const previous = { modules, lessons };
      set((state) => ({
        modules: state.modules.map((item) =>
          item.id === moduleId ? { ...item, lessonIds: ids } : item,
        ),
        lessons: state.lessons.map((item) =>
          ids.includes(item.id) ? { ...item, order: ids.indexOf(item.id) + 1 } : item,
        ),
      }));
      setPending(lockKey, true);
      try {
        await Promise.all(
          ids.map((id, index) => updateLessonApi(course.id, id, { order: index + 1 })),
        );
        const lesson = lessons.find((item) => item.id === lessonId);
        announce(`«${lesson?.title || "Урок"}» теперь на позиции ${to + 1} в модуле «${module.title}».`);
        return true;
      } catch {
        set(previous);
        toast("error", "Не удалось изменить порядок. Предыдущий порядок восстановлен.");
        return false;
      } finally {
        setPending(lockKey, false);
      }
    },

    moveLessonBy: (lessonId, delta) => {
      const module = moduleOfLesson(lessonId);
      if (!module) return;
      const index = module.lessonIds.indexOf(lessonId);
      get().reorderLesson(module.id, lessonId, index + delta);
    },

    reorderModule: async (moduleId, toIndex) => {
      const { course, modules, pending } = get();
      if (!course?.id || pending["order:modules"]) {
        if (pending["order:modules"]) toast("warning", "Порядок модулей ещё сохраняется.");
        return false;
      }
      const ordered = [...modules].sort((a, b) => a.order - b.order);
      const from = ordered.findIndex((item) => item.id === moduleId);
      const to = Math.max(0, Math.min(toIndex, ordered.length - 1));
      if (from < 0 || from === to) return false;
      const [moved] = ordered.splice(from, 1);
      ordered.splice(to, 0, moved);
      const next = ordered.map((item, index) => ({ ...item, order: index + 1 }));
      const previous = modules;
      set({ modules: next });
      setPending("order:modules", true);
      try {
        await Promise.all(
          next.map((item) => updateModuleApi(course.id, item.id, { order: item.order })),
        );
        announce(`Модуль «${moved.title}» теперь на позиции ${to + 1}.`);
        return true;
      } catch {
        set({ modules: previous });
        toast("error", "Не удалось изменить порядок. Предыдущий порядок восстановлен.");
        return false;
      } finally {
        setPending("order:modules", false);
      }
    },

    moveModuleBy: (moduleId, delta) => {
      const ordered = [...get().modules].sort((a, b) => a.order - b.order);
      const index = ordered.findIndex((item) => item.id === moduleId);
      if (index < 0) return;
      get().reorderModule(moduleId, index + delta);
    },

    saveModuleMeta: async (moduleId) => {
      const { course, modules, pending } = get();
      const module = modules.find((item) => item.id === moduleId);
      const key = nodeId.module(moduleId);
      if (!course?.id || !module || pending[key]) return;
      const values = getFormValues(key, "module", module);
      const title = values.title.trim();
      const description = values.description.trim();
      if (!title || !description) {
        setSaveStatus(key, "error", "Заполните название и описание модуля.");
        return;
      }
      const learningObjectives = parseObjectives(values.learningObjectives);
      setPending(key, true);
      setSaveStatus(key, "saving");
      try {
        await updateModuleApi(course.id, moduleId, { title, description, learningObjectives });
        set((state) => ({
          modules: state.modules.map((item) =>
            item.id === moduleId ? { ...item, title, description, learningObjectives } : item,
          ),
        }));
        clearForm(key);
        setSaveStatus(key, "saved");
        toast("success", "Модуль сохранён");
      } catch (error) {
        setSaveStatus(key, "error", getApiErrorMessage(error, "Не удалось сохранить модуль."));
      } finally {
        setPending(key, false);
      }
    },

    deleteModule: async (moduleId) => {
      const { modules, course } = get();
      const module = modules.find((item) => item.id === moduleId);
      const key = nodeId.module(moduleId);
      if (!module || get().pending[key]) return false;
      setPending(key, true);
      try {
        await deleteModuleApi(moduleId);
        // На сервере уроки удаляются вместе с модулем (каскад), поэтому убираем их и здесь.
        const removedLessons = new Set(module.lessonIds);
        const remaining = [...modules]
          .filter((item) => item.id !== moduleId)
          .sort((a, b) => a.order - b.order)
          .map((item, index) => ({ ...item, order: index + 1 }));
        set((state) => {
          const positions = { ...state.positions };
          const forms = { ...state.forms };
          delete forms[key];
          removedLessons.forEach((id) => {
            delete positions[nodeId.lesson(id)];
            delete forms[nodeId.lesson(id)];
          });
          const removedKeys = new Set([key, ...[...removedLessons].map(nodeId.lesson)]);
          return {
            modules: remaining,
            lessons: state.lessons.filter((lesson) => !removedLessons.has(lesson.id)),
            materials: state.materials.map((item) =>
              removedLessons.has(item.lessonId) ? { ...item, lessonId: null } : item,
            ),
            positions,
            forms,
            selectedIds: state.selectedIds.filter((id) => !removedKeys.has(id)),
            activeNodeId: removedKeys.has(state.activeNodeId) ? null : state.activeNodeId,
            inspector: removedKeys.has(state.activeNodeId)
              ? { open: false, tab: null }
              : state.inspector,
          };
        });
        if (course?.id && remaining.length) {
          sendOrderUpdates(remaining, (item) =>
            updateModuleApi(course.id, item.id, { order: item.order }),
          );
        }
        toast("success", "Модуль удалён");
        announce(`Модуль «${module.title}» удалён.`);
        return true;
      } catch (error) {
        toast("error", getApiErrorMessage(error, "Не удалось удалить модуль."));
        return false;
      } finally {
        setPending(key, false);
      }
    },

    // ───────────── Интерфейс ─────────────
    setSelection: (ids) =>
      set((state) => {
        const kept = state.selectedIds.filter((id) => ids.includes(id));
        const added = ids.filter((id) => !kept.includes(id));
        const next = [...kept, ...added];
        if (next.length === state.selectedIds.length && next.every((id, i) => id === state.selectedIds[i])) {
          return {};
        }
        return { selectedIds: next };
      }),

    toggleSelected: (id) =>
      set((state) => ({
        selectedIds: state.selectedIds.includes(id)
          ? state.selectedIds.filter((item) => item !== id)
          : [...state.selectedIds, id],
      })),

    openInspector: (id, tab = null) =>
      set((state) => ({
        activeNodeId: id,
        inspector: {
          open: true,
          tab: tab || (state.activeNodeId === id ? state.inspector.tab : null),
        },
      })),

    setInspectorTab: (tab) =>
      set((state) => ({ inspector: { ...state.inspector, tab } })),

    closeInspector: () =>
      set((state) => ({ inspector: { ...state.inspector, open: false } })),

    updateForm: (key, type, entity, patch) =>
      set((state) => {
        const base = formFromEntity(type, entity);
        const next = { ...(state.forms[key] || base), ...patch };
        const forms = { ...state.forms };
        const saveStatus = { ...state.saveStatus };
        const saveErrors = { ...state.saveErrors };
        delete saveErrors[key];
        if (isSameForm(next, base)) {
          delete forms[key];
          delete saveStatus[key];
        } else {
          forms[key] = next;
          saveStatus[key] = "dirty";
        }
        return { forms, saveStatus, saveErrors };
      }),

    resetForm: (key) => {
      clearForm(key);
      setSaveStatus(key, null);
    },

    setPositions: (patch) =>
      set((state) => ({ positions: { ...state.positions, ...patch } })),

    setViewport: (viewport) => set({ viewport }),
    setFilter: (filter) => set((state) => ({ filter: state.filter === filter ? null : filter })),
    setViewMode: (viewMode) => set({ viewMode }),
    setPaletteOpen: (paletteOpen) => set({ paletteOpen }),
    setDropHint: (dropHint) => set({ dropHint }),
    setDragKind: (dragKind) => set({ dragKind }),
    requestFocus: (ids) => set({ focusRequest: { ids, at: Date.now() } }),
    dismissOnboarding: () => set({ onboardingDismissed: true }),
    setInspectorWidth: (kind, width) =>
      set((state) => ({
        inspectorWidths: { ...(state.inspectorWidths || {}), [kind]: Math.round(width) },
      })),
    toggleFullscreen: () => set((state) => ({ fullscreen: !state.fullscreen })),
    toggleUsedMaterials: () =>
      set((state) => ({ showUsedMaterials: !state.showUsedMaterials })),
    restartOnboarding: () => set({ onboardingDismissed: false }),
    markCelebrated: () => set({ celebrated: true }),

    openMaterialPicker: () => set({ materialPicker: { selected: [] } }),
    closeMaterialPicker: () => set({ materialPicker: null }),
    toggleMaterialPick: (id) =>
      set((state) =>
        state.materialPicker
          ? {
              materialPicker: {
                selected: state.materialPicker.selected.includes(id)
                  ? state.materialPicker.selected.filter((item) => item !== id)
                  : [...state.materialPicker.selected, id],
              },
            }
          : {},
      ),

    openConfirm: (confirm) => set({ confirm }),
    closeConfirm: () => set({ confirm: null }),

    openFinish: () => set({ finishOpen: true, finishError: "" }),
    closeFinish: () => {
      if (get().pending.finish) return;
      set({ finishOpen: false });
    },

    finish: async (onCreateCourse) => {
      const { course, pending } = get();
      if (!course?.id || pending.finish) return;
      setPending("finish", true);
      set({ finishError: "" });
      try {
        await Promise.all(get().lessons.map((lesson) => flushLessonContent(lesson.id)));
        await onCreateCourse({ courseId: course.id });
        setPending("finish", false);
        set({ finishOpen: false });
        get().persistNow();
      } catch (error) {
        setPending("finish", false);
        set({
          finishError: getApiErrorMessage(
            error,
            "Курс сохранён, но открыть просмотр курса не удалось. Попробуйте ещё раз.",
          ),
        });
      }
    },

    /** Собирает холст по курсу с сервера, если локального черновика этого курса нет. */
    loadFromServer: async (courseId) => {
      const { course, modules } = await fetchCourseStructure(courseId);
      const lessonsWithContent = await Promise.all(
        modules.flatMap((module) =>
          module.lessons.map(async (lesson, index) => ({
            ...normalizeLesson(lesson, { order: index + 1 }),
            contentBlocks: await fetchLessonBlocks(lesson.id).catch(() => []),
            moduleId: module.id,
            materialIds: [],
            isLocal: false,
          })),
        ),
      );
      fileRegistry.clear();
      set({
        ...EMPTY_DRAFT,
        ...TRANSIENT,
        hydrated: true,
        course: normalizeCourse(course, { id: courseId }),
        modules: modules.map((module, index) => ({
          ...normalizeModule(module, { order: index + 1 }),
          lessonIds: module.lessons.map((lesson) => lesson.id),
        })),
        lessons: lessonsWithContent,
        onboardingDismissed: true,
        celebrated: true,
        focusRequest: { ids: ["course"], at: Date.now() },
      });
      get().persistNow();
    },

    resetAll: ({ silent = false } = {}) => {
      fileRegistry.clear();
      contentTimers.forEach((timer) => window.clearTimeout(timer));
      contentTimers.clear();
      set({ ...EMPTY_DRAFT, ...TRANSIENT, hydrated: true });
      clearDraft();
      if (!silent) toast("info", "Черновик конструктора очищен. Созданный курс остался на сервере.");
    },
  };
});
