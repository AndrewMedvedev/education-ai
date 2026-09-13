import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import LessonContentEditor from "../components/LessonContentEditor";
import SectionTop from "../components/SectionTop";
import { MAX_CONTENT_BLOCKS } from "../lesson/lessonEditorConfig";
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
  updateCourse as updateCourseApi,
  updateLesson as updateLessonApi,
  updateModule as updateModuleApi,
  updateLessonContentBlocks,
  uploadDocument,
  isAuthenticated,
  redirectToLogin,
} from "../utils/api";
import { getLocalStorage } from "../utils/storage";

const MAX_FILE_SIZE_BYTES = 30 * 1024 * 1024;
const MANUAL_BUILDER_DRAFT_KEY = "manual_course_builder_draft_v1";

const EMPTY_MODULE_DRAFT = {
  title: "",
  description: "",
  learningObjectives: "",
};

const EMPTY_STRUCTURE_DRAFT = {
  title: "",
  description: "",
  learningObjectives: "",
  estimatedTimeMinutes: "",
};

const EMPTY_LESSON_DRAFT = {
  title: "",
  description: "",
  learningObjectives: "",
  estimatedTimeMinutes: "",
};

const EMPTY_COURSE_DRAFT = {
  title: "",
  description: "",
  difficulty: "beginner",
  tags: "",
};

function createBlockDraft(file, index) {
  return {
    id: `manual-block-${Date.now()}-${index}`,
    file,
    blockNumber: index + 1,
    status: file.size > MAX_FILE_SIZE_BYTES ? "error" : "uploading",
    selected: false,
    markdown: "",
    proposal: null,
    error:
      file.size > MAX_FILE_SIZE_BYTES
        ? "Файл больше 30 МБ. Его нельзя отправить на backend."
        : "",
  };
}

function parseObjectives(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function blocksToTextContentBlocks(items) {
  return items
    .map((block) => ({
      content_type: "text",
      ai_generated: false,
      md_content: block.markdown || "",
    }))
    .filter((block) => block.md_content.trim());
}

function lessonContentToMarkdown(lesson) {
  const contentBlocks = lesson?.contentBlocks || lesson?.content_blocks || [];
  if (contentBlocks.length > 0) {
    return contentBlocks
      .map((block) => block.md_content || block.markdown || block.content || "")
      .filter(Boolean)
      .join("\n\n---\n\n");
  }
  return lesson?.markdown || lesson?.content || "";
}

function markdownToTextContentBlocks(markdown) {
  const text = markdown.trim();
  return text
    ? [
        {
          content_type: "text",
          ai_generated: false,
          md_content: text,
        },
      ]
    : [];
}

function withoutFile(block) {
  if (!block) return block;
  const { file, ...rest } = block;
  return {
    ...rest,
    fileName: rest.fileName || file?.name || "",
    status: rest.status === "uploading" ? "error" : rest.status,
    error:
      rest.status === "uploading"
        ? "Загрузка была прервана обновлением страницы. Добавьте файл заново или используйте уже сохранённый markdown."
        : rest.error || "",
  };
}

function loadManualBuilderDraft() {
  const storage = getLocalStorage();
  if (!storage) return {};

  try {
    const parsed = JSON.parse(
      storage.getItem(MANUAL_BUILDER_DRAFT_KEY) || "null",
    );
    if (!parsed || typeof parsed !== "object") return {};

    return {
      blocks: Array.isArray(parsed.blocks)
        ? parsed.blocks.map(withoutFile)
        : [],
      lessons: Array.isArray(parsed.lessons) ? parsed.lessons : [],
      selectedLessonIds: Array.isArray(parsed.selectedLessonIds)
        ? parsed.selectedLessonIds
        : [],
      modules: Array.isArray(parsed.modules) ? parsed.modules : [],
      moduleDraft: parsed.moduleDraft || EMPTY_MODULE_DRAFT,
      editingStructure: parsed.editingStructure || null,
      structureDraft: parsed.structureDraft || EMPTY_STRUCTURE_DRAFT,
      activeLessonId: parsed.activeLessonId || null,
      activeLessonDraft: parsed.activeLessonDraft || EMPTY_LESSON_DRAFT,
      lessonContentDraft: parsed.lessonContentDraft || "",
      courseDraft: parsed.courseDraft || EMPTY_COURSE_DRAFT,
      createdCourse: parsed.createdCourse || null,
      isCourseFormOpen: parsed.isCourseFormOpen ?? !parsed.createdCourse?.id,
      editingBlockId: parsed.editingBlockId || null,
      chatBlockId: parsed.chatBlockId || null,
      isModuleFormOpen: Boolean(parsed.isModuleFormOpen),
      transferTargetModuleId: parsed.transferTargetModuleId || "",
    };
  } catch {
    return {};
  }
}

function saveManualBuilderDraft(draft) {
  const storage = getLocalStorage();
  if (!storage) return;

  storage.setItem(
    MANUAL_BUILDER_DRAFT_KEY,
    JSON.stringify({
      ...draft,
      blocks: (draft.blocks || []).map(withoutFile),
    }),
  );
}

function clearManualBuilderDraft() {
  getLocalStorage()?.removeItem(MANUAL_BUILDER_DRAFT_KEY);
}

function getApiErrorMessage(error, fallback) {
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

const DIFFICULTY_OPTIONS = [
  { value: "beginner", label: "Начальный" },
  { value: "intermediate", label: "Средний" },
  { value: "advanced", label: "Продвинутый" },
  { value: "expert", label: "Экспертный" },
];

export default function ManualCourseBuilderPage({ onCreateCourse }) {
  const fileInputRef = useRef(null);
  const restoredDraftRef = useRef(loadManualBuilderDraft());
  const restoredDraft = restoredDraftRef.current;

  const [blocks, setBlocks] = useState(restoredDraft.blocks || []);
  const [pendingBlockFocusId, setPendingBlockFocusId] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const [lessons, setLessons] = useState(restoredDraft.lessons || []);
  const [selectedLessonIds, setSelectedLessonIds] = useState(
    restoredDraft.selectedLessonIds || [],
  );

  const [modules, setModules] = useState(restoredDraft.modules || []);
  const [draggedModuleId, setDraggedModuleId] = useState(null);
  const [dragOverModuleId, setDragOverModuleId] = useState(null);
  const [draggedLessonId, setDraggedLessonId] = useState(null);
  const [dragOverLessonId, setDragOverLessonId] = useState(null);
  const [isReorderingModules, setIsReorderingModules] = useState(false);
  const [isReorderingLessons, setIsReorderingLessons] = useState(false);
  const [isMovingDraggedLesson, setIsMovingDraggedLesson] = useState(false);
  const [deletingTreeItemId, setDeletingTreeItemId] = useState(null);
  const [treeActionError, setTreeActionError] = useState("");
  const [isCreatingLesson, setIsCreatingLesson] = useState(false);
  const [lessonCreateError, setLessonCreateError] = useState("");
  const [isModuleFormOpen, setIsModuleFormOpen] = useState(
    restoredDraft.isModuleFormOpen || false,
  );
  const [isCreatingModule, setIsCreatingModule] = useState(false);
  const [isMovingLessons, setIsMovingLessons] = useState(false);
  const [transferTargetModuleId, setTransferTargetModuleId] = useState(
    restoredDraft.transferTargetModuleId || "",
  );
  const [moduleCreateError, setModuleCreateError] = useState("");
  const [moduleDraft, setModuleDraft] = useState(
    restoredDraft.moduleDraft || EMPTY_MODULE_DRAFT,
  );
  const [editingStructure, setEditingStructure] = useState(
    restoredDraft.editingStructure || null,
  );
  const [structureDraft, setStructureDraft] = useState(
    restoredDraft.structureDraft || EMPTY_STRUCTURE_DRAFT,
  );
  const [structureEditError, setStructureEditError] = useState("");
  const [isSavingStructure, setIsSavingStructure] = useState(false);
  const [activeLessonId, setActiveLessonId] = useState(
    restoredDraft.activeLessonId || null,
  );
  const [activeLessonDraft, setActiveLessonDraft] = useState(
    restoredDraft.activeLessonDraft || EMPTY_LESSON_DRAFT,
  );
  const [lessonContentDraft, setLessonContentDraft] = useState(
    restoredDraft.lessonContentDraft || "",
  );
  const [lessonContentError, setLessonContentError] = useState("");
  const [lessonMetaError, setLessonMetaError] = useState("");
  const [isSavingLessonContent, setIsSavingLessonContent] = useState(false);
  const [isSavingLessonMeta, setIsSavingLessonMeta] = useState(false);
  const [courseDraft, setCourseDraft] = useState(
    restoredDraft.courseDraft || EMPTY_COURSE_DRAFT,
  );
  const [createdCourse, setCreatedCourse] = useState(
    restoredDraft.createdCourse || null,
  );
  const [isCourseFormOpen, setIsCourseFormOpen] = useState(
    restoredDraft.isCourseFormOpen ?? !restoredDraft.createdCourse?.id,
  );
  const [courseCreateError, setCourseCreateError] = useState("");
  const [isCreatingCourse, setIsCreatingCourse] = useState(false);
  const [finishError, setFinishError] = useState("");
  const [isFinishing, setIsFinishing] = useState(false);

  const [editingBlockId, setEditingBlockId] = useState(
    restoredDraft.editingBlockId || null,
  );
  const [chatBlockId, setChatBlockId] = useState(
    restoredDraft.chatBlockId || null,
  );

  const [aiInput, setAiInput] = useState("");
  const [proposalError, setProposalError] = useState("");
  const aiMessagesRef = useRef(null);

  const availableBlocks = blocks.filter((block) => !block.lessonId);
  const readyBlocks = availableBlocks.filter(
    (block) => block.status === "ready",
  );
  const selectedBlocks = readyBlocks.filter((block) => block.selected);
  const activeChatBlock =
    blocks.find((block) => block.id === chatBlockId) || null;
  const aiConversationKey = createAgentConversationKey(
    "editor",
    createdCourse?.id,
    `manual:${chatBlockId || "none"}`,
  );
  const aiConversation = useAgentStore(
    (state) => state.conversations[aiConversationKey],
  );
  const sendAgentMessage = useAgentStore((state) => state.sendMessage);
  const cancelAgentRequest = useAgentStore((state) => state.cancelRequest);
  const isAiSending = aiConversation?.status === "loading";
  const aiError = proposalError || aiConversation?.error || "";
  const activeLesson =
    lessons.find((lesson) => lesson.id === activeLessonId) || null;
  const activeModule =
    editingStructure?.type === "module"
      ? modules.find((module) => module.id === editingStructure.id) || null
      : null;

  const hasCreatedCourse = Boolean(createdCourse?.id);
  const hasBlocks = blocks.length > 0;
  const hasLessons = lessons.length > 0;
  const hasModules = modules.length > 0;
  const canCreateLesson = selectedBlocks.length > 0 && !isCreatingLesson;
  const assignedLessonIds = new Set(
    modules.flatMap((module) => module.lessonIds || []),
  );
  const selectedLessons = lessons.filter((lesson) =>
    selectedLessonIds.includes(lesson.id),
  );
  const selectedLessonsAreAssigned =
    selectedLessons.length > 0 &&
    selectedLessons.every((lesson) => assignedLessonIds.has(lesson.id));
  const selectedLessonsAreUnassigned =
    selectedLessons.length > 0 &&
    selectedLessons.every((lesson) => !assignedLessonIds.has(lesson.id));
  const selectedSourceModuleIds = new Set(
    modules
      .filter((module) =>
        (module.lessonIds || []).some((lessonId) =>
          selectedLessonIds.includes(lessonId),
        ),
      )
      .map((module) => module.id),
  );
  const transferTargetModules = modules.filter(
    (module) => !selectedSourceModuleIds.has(module.id),
  );
  const selectedTransferTargetId = transferTargetModules.some(
    (module) => module.id === transferTargetModuleId,
  )
    ? transferTargetModuleId
    : transferTargetModules[0]?.id || "";
  const canCreateModule =
    selectedLessonsAreUnassigned && !isCreatingModule && !isMovingLessons;
  const canMoveLessons =
    selectedLessonsAreAssigned &&
    Boolean(selectedTransferTargetId) &&
    !isCreatingModule &&
    !isMovingLessons;
  const unassignedLessons = lessons.filter(
    (lesson) => !assignedLessonIds.has(lesson.id),
  );
  const courseTreeModules = [
    ...modules,
    ...(unassignedLessons.length > 0
      ? [
          {
            id: "manual-module-draft",
            title: "Уроки без модуля",
            lessonIds: unassignedLessons.map((lesson) => lesson.id),
            isDraft: true,
          },
        ]
      : []),
  ];

  useEffect(
    () => () => cancelAgentRequest(aiConversationKey),
    [aiConversationKey, cancelAgentRequest],
  );

  useEffect(() => {
    saveManualBuilderDraft({
      blocks,
      lessons,
      selectedLessonIds,
      modules,
      moduleDraft,
      editingStructure,
      structureDraft,
      activeLessonId,
      activeLessonDraft,
      lessonContentDraft,
      courseDraft,
      createdCourse,
      isCourseFormOpen,
      editingBlockId,
      chatBlockId,
      isModuleFormOpen,
      transferTargetModuleId,
    });
  }, [
    activeLessonDraft,
    activeLessonId,
    blocks,
    chatBlockId,
    courseDraft,
    createdCourse,
    editingBlockId,
    isCourseFormOpen,
    editingStructure,
    isModuleFormOpen,
    lessonContentDraft,
    lessons,
    moduleDraft,
    modules,
    selectedLessonIds,
    structureDraft,
    transferTargetModuleId,
  ]);

  useEffect(() => {
    const container = aiMessagesRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [aiConversation?.messages, isAiSending]);

  useEffect(() => {
    if (modules.length >= 2) {
      return;
    }

    setSelectedLessonIds((current) => {
      const next = current.filter(
        (lessonId) => !assignedLessonIds.has(lessonId),
      );
      return next.length === current.length ? current : next;
    });
  }, [modules.length]);

  useEffect(() => {
    if (!pendingBlockFocusId) {
      return undefined;
    }

    const frameId = window.requestAnimationFrame(() => {
      const blockElement = document.getElementById(pendingBlockFocusId);
      if (!blockElement) {
        return;
      }

      blockElement.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });
      setPendingBlockFocusId(null);
    });

    return () => window.cancelAnimationFrame(frameId);
  }, [pendingBlockFocusId, blocks]);

  const uploadBlock = async (blockDraft) => {
    if (!hasCreatedCourse || blockDraft.status === "error") {
      return;
    }

    if (!isAuthenticated()) {
      redirectToLogin();
      return;
    }

    try {
      const markdown = await uploadDocument(blockDraft.file);

      setBlocks((prev) =>
        prev.map((block) =>
          block.id === blockDraft.id
            ? {
                ...block,
                status: "ready",
                markdown,
              }
            : block,
        ),
      );
    } catch (error) {
      const errorMessage = getApiErrorMessage(
        error,
        "Не удалось обработать материал.",
      );
      setBlocks((prev) =>
        prev.map((block) =>
          block.id === blockDraft.id
            ? {
                ...block,
                status: "error",
                error: errorMessage,
              }
            : block,
        ),
      );
    }
  };

  const handleFiles = async (fileList) => {
    if (!hasCreatedCourse) {
      return;
    }

    const pickedFiles = Array.from(fileList || []);

    if (pickedFiles.length === 0) {
      return;
    }

    const startIndex = blocks.length;
    const drafts = pickedFiles.map((file, index) =>
      createBlockDraft(file, startIndex + index),
    );

    setActiveLessonId(null);
    setEditingStructure(null);
    setIsModuleFormOpen(false);
    setBlocks((prev) => [...prev, ...drafts]);
    setPendingBlockFocusId(drafts[0].id);

    drafts.forEach((draft) => {
      if (draft.status !== "error") {
        uploadBlock(draft);
      }
    });
  };

  const toggleBlockSelection = (blockId) => {
    setBlocks((prev) =>
      prev.map((block) =>
        block.id === blockId ? { ...block, selected: !block.selected } : block,
      ),
    );
  };

  const updateBlockMarkdown = (blockId, markdown) => {
    setBlocks((prev) =>
      prev.map((block) =>
        block.id === blockId ? { ...block, markdown } : block,
      ),
    );
  };

  const toggleBlockEditing = (blockId) => {
    setEditingBlockId((current) => (current === blockId ? null : blockId));
  };

  const deleteAvailableBlock = (blockId) => {
    const block = availableBlocks.find((item) => item.id === blockId);
    if (!block || !window.confirm(`Удалить блок ${block.blockNumber}?`)) {
      return;
    }

    setBlocks((prev) => prev.filter((item) => item.id !== blockId));
    setEditingBlockId((current) => (current === blockId ? null : current));
    setChatBlockId((current) => (current === blockId ? null : current));
  };

  const reorderModules = async (targetModuleId) => {
    if (
      !draggedModuleId ||
      draggedModuleId === targetModuleId ||
      isReorderingModules
    ) {
      setDraggedModuleId(null);
      setDragOverModuleId(null);
      return;
    }

    const draggedIndex = modules.findIndex(
      (module) => module.id === draggedModuleId,
    );
    const targetIndex = modules.findIndex(
      (module) => module.id === targetModuleId,
    );
    if (draggedIndex < 0 || targetIndex < 0) {
      return;
    }

    const previousModules = modules;
    const reorderedModules = [...modules];
    const [draggedModule] = reorderedModules.splice(draggedIndex, 1);
    reorderedModules.splice(targetIndex, 0, draggedModule);
    const orderedModules = reorderedModules.map((module, index) => ({
      ...module,
      order: index + 1,
    }));

    setModules(orderedModules);
    setDraggedModuleId(null);
    setDragOverModuleId(null);
    setIsReorderingModules(true);
    setTreeActionError("");

    try {
      await Promise.all(
        orderedModules.map((module) =>
          updateModuleApi(createdCourse.id, module.id, {
            order: module.order,
          }),
        ),
      );
    } catch (error) {
      setModules(previousModules);
      setTreeActionError(
        getApiErrorMessage(error, "Не удалось изменить порядок модулей."),
      );
    } finally {
      setIsReorderingModules(false);
    }
  };

  const moveUnassignedLessonToModule = async (lessonId, targetModule) => {
    const lesson = lessons.find((item) => item.id === lessonId);
    if (
      !lesson ||
      targetModule.isDraft ||
      assignedLessonIds.has(lessonId) ||
      isMovingDraggedLesson
    ) {
      setDraggedLessonId(null);
      setDragOverModuleId(null);
      return;
    }

    const order = (targetModule.lessonIds || []).length + 1;
    setIsMovingDraggedLesson(true);
    setTreeActionError("");

    try {
      await assignLessonToModule(lesson.id, targetModule.id);
      try {
        await updateLessonApi(createdCourse.id, lesson.id, { order });
      } catch (orderError) {
        setTreeActionError(
          getApiErrorMessage(
            orderError,
            "Урок добавлен в модуль, но его позицию не удалось сохранить.",
          ),
        );
      }

      setModules((prev) =>
        prev.map((module) =>
          module.id === targetModule.id
            ? {
                ...module,
                lessonIds: [...(module.lessonIds || []), lesson.id],
              }
            : module,
        ),
      );
      setLessons((prev) =>
        prev.map((item) =>
          item.id === lesson.id
            ? {
                ...item,
                moduleId: targetModule.id,
                module_id: targetModule.id,
                order,
              }
            : item,
        ),
      );
      setSelectedLessonIds((prev) =>
        prev.filter((selectedId) => selectedId !== lesson.id),
      );
    } catch (error) {
      setTreeActionError(
        getApiErrorMessage(error, "Не удалось добавить урок в модуль."),
      );
    } finally {
      setIsMovingDraggedLesson(false);
      setDraggedLessonId(null);
      setDragOverModuleId(null);
    }
  };

  const reorderLessons = async (module, targetLessonId) => {
    if (
      !draggedLessonId ||
      draggedLessonId === targetLessonId ||
      isReorderingLessons
    ) {
      setDraggedLessonId(null);
      setDragOverLessonId(null);
      return;
    }

    const lessonIds = [...(module.lessonIds || [])];
    const draggedIndex = lessonIds.indexOf(draggedLessonId);
    const targetIndex = lessonIds.indexOf(targetLessonId);
    if (draggedIndex < 0 || targetIndex < 0) {
      setDraggedLessonId(null);
      setDragOverLessonId(null);
      return;
    }

    const previousLessons = lessons;
    const previousModules = modules;
    const [movedLessonId] = lessonIds.splice(draggedIndex, 1);
    lessonIds.splice(targetIndex, 0, movedLessonId);
    const lessonById = new Map(lessons.map((lesson) => [lesson.id, lesson]));
    const orderedLessons = lessonIds.map((lessonId, index) => ({
      ...lessonById.get(lessonId),
      order: index + 1,
    }));
    const orderedLessonById = new Map(
      orderedLessons.map((lesson) => [lesson.id, lesson]),
    );
    let orderedIndex = 0;
    const nextLessons = lessons.map((lesson) =>
      orderedLessonById.has(lesson.id)
        ? orderedLessons[orderedIndex++]
        : lesson,
    );
    const nextModules = module.isDraft
      ? modules
      : modules.map((item) =>
          item.id === module.id ? { ...item, lessonIds } : item,
        );

    setLessons(nextLessons);
    setModules(nextModules);
    setDraggedLessonId(null);
    setDragOverLessonId(null);
    setIsReorderingLessons(true);
    setTreeActionError("");

    try {
      await Promise.all(
        orderedLessons.map((lesson) =>
          updateLessonApi(createdCourse.id, lesson.id, {
            order: lesson.order,
          }),
        ),
      );
    } catch (error) {
      setLessons(previousLessons);
      setModules(previousModules);
      setTreeActionError(
        getApiErrorMessage(error, "Не удалось изменить порядок уроков."),
      );
    } finally {
      setIsReorderingLessons(false);
    }
  };

  const deleteCourseModule = async (module) => {
    if (
      module.isDraft ||
      deletingTreeItemId ||
      !window.confirm(`Удалить модуль «${module.title}»?`)
    ) {
      return;
    }

    setDeletingTreeItemId(module.id);
    setTreeActionError("");

    try {
      await deleteModuleApi(module.id);
      const remainingModules = modules
        .filter((item) => item.id !== module.id)
        .map((item, index) => ({ ...item, order: index + 1 }));
      setModules(remainingModules);
      setLessons((prev) =>
        prev.map((lesson) =>
          (module.lessonIds || []).includes(lesson.id)
            ? { ...lesson, moduleId: null, module_id: null }
            : lesson,
        ),
      );
      setEditingStructure((current) =>
        current?.type === "module" && current.id === module.id ? null : current,
      );
      await Promise.all(
        remainingModules.map((item) =>
          updateModuleApi(createdCourse.id, item.id, { order: item.order }),
        ),
      );
    } catch (error) {
      setTreeActionError(
        getApiErrorMessage(error, "Не удалось удалить модуль."),
      );
    } finally {
      setDeletingTreeItemId(null);
    }
  };

  const deleteCourseLesson = async (lesson) => {
    if (
      deletingTreeItemId ||
      !window.confirm(`Удалить урок «${lesson.title}»?`)
    ) {
      return;
    }

    const parentModule = modules.find((module) =>
      (module.lessonIds || []).includes(lesson.id),
    );
    const shouldDeleteParent = parentModule?.lessonIds?.length === 1;
    setDeletingTreeItemId(lesson.id);
    setTreeActionError("");

    try {
      await deleteLessonApi(lesson.id);

      if (shouldDeleteParent) {
        await deleteModuleApi(parentModule.id).catch(() => null);
      }

      setLessons((prev) => prev.filter((item) => item.id !== lesson.id));
      setBlocks((prev) =>
        prev.map((block) =>
          block.lessonId === lesson.id
            ? { ...block, lessonId: null, selected: false }
            : block,
        ),
      );
      setSelectedLessonIds((prev) =>
        prev.filter((lessonId) => lessonId !== lesson.id),
      );
      setActiveLessonId((current) => (current === lesson.id ? null : current));
      setModules((prev) =>
        prev
          .filter(
            (module) => !shouldDeleteParent || module.id !== parentModule.id,
          )
          .map((module, index) => ({
            ...module,
            order: index + 1,
            lessonIds: (module.lessonIds || []).filter(
              (lessonId) => lessonId !== lesson.id,
            ),
          })),
      );
    } catch (error) {
      setTreeActionError(getApiErrorMessage(error, "Не удалось удалить урок."));
    } finally {
      setDeletingTreeItemId(null);
    }
  };

  const toggleBlockChat = (blockId) => {
    setChatBlockId((current) => (current === blockId ? null : blockId));
    setAiInput("");
    setProposalError("");
  };

  const closeBlockAiEditor = () => {
    setChatBlockId(null);
    setAiInput("");
    setProposalError("");
  };

  const askBlockAi = async () => {
    const prompt = aiInput.trim();
    if (!prompt || !activeChatBlock || !createdCourse?.id || isAiSending) {
      return;
    }

    const currentMarkdown = activeChatBlock.markdown || "";
    setProposalError("");
    setAiInput("");

    try {
      const response = await sendAgentMessage({
        key: aiConversationKey,
        agent: "editor",
        courseId: createdCourse?.id,
        content: prompt,
        contentBlocks: blocksToTextContentBlocks(
          availableBlocks.filter((block) => block.id !== activeChatBlock.id),
        ),
        editorPayload: {
          content_type: "text",
          content_block: JSON.stringify({
            content_type: "text",
            ai_generated: false,
            md_content: currentMarkdown,
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
        setProposalError(
          "ИИ вернул ответ в неподдерживаемом формате. Попробуйте уточнить запрос.",
        );
        return;
      }

      setBlocks((prev) =>
        prev.map((block) =>
          block.id === activeChatBlock.id
            ? { ...block, proposal: proposal.trim() }
            : block,
        ),
      );
    } catch {
      // Публичная сетевая ошибка хранится в Zustand-store.
    }
  };

  const applyBlockProposal = (blockId) => {
    setBlocks((prev) =>
      prev.map((block) => {
        if (block.id !== blockId || !block.proposal) {
          return block;
        }
        return { ...block, markdown: block.proposal, proposal: null };
      }),
    );
    setChatBlockId(null);
  };

  const rejectBlockProposal = (blockId) => {
    setBlocks((prev) =>
      prev.map((block) =>
        block.id === blockId ? { ...block, proposal: null } : block,
      ),
    );
  };

  const mergeSelectedBlocksIntoLesson = async () => {
    if (!canCreateLesson || !createdCourse?.id) {
      return;
    }

    const selected = selectedBlocks.map((block) => block.id);
    const lessonNumber = lessons.length + 1;
    const contentBlocks = blocksToTextContentBlocks(selectedBlocks);

    if (contentBlocks.length === 0) {
      setLessonCreateError("Нет готового контента для сохранения урока.");
      return;
    }
    if (contentBlocks.length > MAX_CONTENT_BLOCKS) {
      setLessonCreateError(
        `В одном уроке может быть не более ${MAX_CONTENT_BLOCKS} блоков.`,
      );
      return;
    }

    setIsCreatingLesson(true);
    setLessonCreateError("");

    try {
      const savedLesson = await createLessonApi({
        title: `Урок ${lessonNumber}`,
        description: `Материалы урока ${lessonNumber}`,
        order: lessonNumber,
        learningObjectives: [],
        contentBlocks,
        estimatedTimeMinutes: null,
      });

      const lessonWithContent = await updateLessonContentBlocks(
        savedLesson.id,
        contentBlocks,
      );

      const lesson = {
        ...savedLesson,
        ...lessonWithContent,
        id: savedLesson.id,
        title:
          lessonWithContent.title ||
          savedLesson.title ||
          `Урок ${lessonNumber}`,
        description:
          lessonWithContent.description || savedLesson.description || "",
        summary: lessonWithContent.summary || savedLesson.summary || "",
        order: lessonNumber,
        blockIds: selected,
        contentBlocks,
        content_blocks: contentBlocks,
      };

      setLessons((prev) => [...prev, lesson]);
      setActiveLessonId(null);
      setEditingStructure(null);
      setLessonContentDraft("");
      setBlocks((prev) =>
        prev.map((block) =>
          selected.includes(block.id)
            ? { ...block, selected: false, lessonId: lesson.id }
            : { ...block, selected: false },
        ),
      );
    } catch (error) {
      setLessonCreateError(
        getApiErrorMessage(error, "Не удалось сохранить урок."),
      );
    } finally {
      setIsCreatingLesson(false);
    }
  };

  const toggleLessonSelection = (lessonId) => {
    const lessonIsAssigned = assignedLessonIds.has(lessonId);

    setSelectedLessonIds((prev) => {
      if (prev.includes(lessonId)) {
        return prev.filter((id) => id !== lessonId);
      }

      const currentSelectionIsAssigned = prev.some((id) =>
        assignedLessonIds.has(id),
      );
      if (prev.length > 0 && currentSelectionIsAssigned !== lessonIsAssigned) {
        return [lessonId];
      }

      return [...prev, lessonId];
    });
    setModuleCreateError("");
    setIsModuleFormOpen(false);
  };

  const openModuleForm = () => {
    if (!canCreateModule) {
      return;
    }

    const moduleNumber = modules.length + 1;
    setModuleDraft({
      title: `Модуль ${moduleNumber}`,
      description: "",
      learningObjectives: "",
    });
    setModuleCreateError("");
    setIsModuleFormOpen(true);
  };

  const submitModuleDraft = async (event) => {
    event.preventDefault();

    if (!canCreateModule || !createdCourse?.id) {
      return;
    }

    const title = moduleDraft.title.trim();
    const description = moduleDraft.description.trim();

    if (!title || !description) {
      setModuleCreateError("Заполните название и описание модуля.");
      return;
    }

    const moduleNumber = modules.length + 1;
    const selectedLessons = lessons.filter((lesson) =>
      selectedLessonIds.includes(lesson.id),
    );

    setIsCreatingModule(true);
    setModuleCreateError("");

    let createdModuleId = null;
    const assignedLessons = [];
    const originalLessonOrders = new Map(
      selectedLessons.map((lesson, index) => [
        lesson.id,
        Number.isFinite(lesson.order) ? lesson.order : index + 1,
      ]),
    );

    try {
      const savedModule = await createModuleApi(createdCourse.id, {
        title,
        description,
        order: moduleNumber,
        learningObjectives: parseObjectives(moduleDraft.learningObjectives),
      });

      if (!savedModule?.id || savedModule.id === createdCourse.id) {
        throw new Error(
          "Backend не вернул корректный id модуля для привязки уроков.",
        );
      }
      createdModuleId = savedModule.id;

      for (const [lessonIndex, lesson] of selectedLessons.entries()) {
        const order = lessonIndex + 1;
        await assignLessonToModule(lesson.id, savedModule.id);
        assignedLessons.push(lesson);
        await updateLessonApi(createdCourse.id, lesson.id, { order });
        await updateLessonContentBlocks(
          lesson.id,
          lesson.contentBlocks || lesson.content_blocks || [],
        );
      }

      const nextModule = {
        ...savedModule,
        id: savedModule.id,
        title: savedModule.title || title,
        description: savedModule.description || description,
        order: moduleNumber,
        learningObjectives:
          savedModule.learningObjectives ||
          parseObjectives(moduleDraft.learningObjectives),
        lessonIds: selectedLessons.map((lesson) => lesson.id),
      };

      setModules((prev) => [...prev, nextModule]);
      setLessons((prev) =>
        prev.map((lesson) => {
          const nextOrder = selectedLessons.findIndex(
            (selectedLesson) => selectedLesson.id === lesson.id,
          );
          return nextOrder >= 0
            ? {
                ...lesson,
                moduleId: savedModule.id,
                module_id: savedModule.id,
                order: nextOrder + 1,
              }
            : lesson;
        }),
      );
      setSelectedLessonIds([]);
      setIsModuleFormOpen(false);
    } catch (error) {
      const rollbackErrors = [];

      if (createdModuleId) {
        try {
          await deleteModuleApi(createdModuleId);
        } catch (rollbackError) {
          rollbackErrors.push(rollbackError);
        }
      }

      const orderRollbackResults = await Promise.allSettled(
        assignedLessons.map((lesson) =>
          updateLessonApi(createdCourse.id, lesson.id, {
            order: originalLessonOrders.get(lesson.id),
          }),
        ),
      );
      if (orderRollbackResults.some((result) => result.status === "rejected")) {
        rollbackErrors.push(
          new Error("Не удалось восстановить порядок уроков."),
        );
      }

      const originalError = getApiErrorMessage(
        error,
        "Не удалось сохранить модуль.",
      );
      setModuleCreateError(
        rollbackErrors.length > 0
          ? `${originalError} Автоматический откат выполнен не полностью.`
          : `${originalError} Изменения автоматически отменены.`,
      );
    } finally {
      setIsCreatingModule(false);
    }
  };

  const moveSelectedLessonsToModule = async () => {
    if (!canMoveLessons || !createdCourse?.id) {
      return;
    }

    const targetModule = modules.find(
      (module) => module.id === selectedTransferTargetId,
    );
    if (!targetModule) {
      return;
    }

    const targetLessonCount = (targetModule.lessonIds || []).length;
    setIsMovingLessons(true);
    setModuleCreateError("");

    try {
      for (const [lessonIndex, lesson] of selectedLessons.entries()) {
        const order = targetLessonCount + lessonIndex + 1;
        await assignLessonToModule(lesson.id, targetModule.id);
        await updateLessonApi(createdCourse.id, lesson.id, { order });
      }

      const movedLessonIds = new Set(selectedLessonIds);
      const emptiedModules = modules.filter(
        (module) =>
          module.id !== targetModule.id &&
          (module.lessonIds || []).length > 0 &&
          (module.lessonIds || []).every((lessonId) =>
            movedLessonIds.has(lessonId),
          ),
      );
      await Promise.allSettled(
        emptiedModules.map((module) => deleteModuleApi(module.id)),
      );

      const emptiedModuleIds = new Set(
        emptiedModules.map((module) => module.id),
      );
      const nextModules = modules
        .filter((module) => !emptiedModuleIds.has(module.id))
        .map((module) => {
          const remainingLessonIds = (module.lessonIds || []).filter(
            (lessonId) => !movedLessonIds.has(lessonId),
          );
          return module.id === targetModule.id
            ? {
                ...module,
                lessonIds: [...remainingLessonIds, ...selectedLessonIds],
              }
            : { ...module, lessonIds: remainingLessonIds };
        })
        .map((module, index) => ({ ...module, order: index + 1 }));
      setModules(nextModules);
      await Promise.allSettled(
        nextModules.map((module) =>
          updateModuleApi(createdCourse.id, module.id, { order: module.order }),
        ),
      );
      setLessons((prev) =>
        prev.map((lesson) => {
          const movedIndex = selectedLessonIds.indexOf(lesson.id);
          return movedIndex >= 0
            ? {
                ...lesson,
                moduleId: targetModule.id,
                module_id: targetModule.id,
                order: targetLessonCount + movedIndex + 1,
              }
            : lesson;
        }),
      );
      setSelectedLessonIds([]);
      setTransferTargetModuleId("");
    } catch (error) {
      setModuleCreateError(
        getApiErrorMessage(
          error,
          "Не удалось перенести уроки в другой модуль.",
        ),
      );
    } finally {
      setIsMovingLessons(false);
    }
  };

  const updateModuleDraft = (field, value) => {
    setModuleDraft((prev) => ({ ...prev, [field]: value }));
  };

  const openLessonContent = (lesson) => {
    setEditingStructure(null);
    setActiveLessonId(lesson.id);
    setActiveLessonDraft({
      title: lesson.title || "",
      description: lesson.description || lesson.summary || "",
      learningObjectives: (
        lesson.learningObjectives ||
        lesson.learning_objectives ||
        []
      ).join("\n"),
      estimatedTimeMinutes:
        lesson.estimated_time_minutes || lesson.estimatedTimeMinutes || "",
    });
    setLessonContentDraft(lessonContentToMarkdown(lesson));
    setLessonContentError("");
    setLessonMetaError("");
  };

  const updateActiveLessonDraft = (field, value) => {
    setActiveLessonDraft((prev) => ({ ...prev, [field]: value }));
  };

  const saveLessonMetadata = async () => {
    if (!activeLesson || !createdCourse?.id) {
      return;
    }

    const title = activeLessonDraft.title.trim();
    const description = activeLessonDraft.description.trim();

    if (!title || !description) {
      setLessonMetaError("Заполните название и описание урока.");
      return;
    }

    setIsSavingLessonMeta(true);
    setLessonMetaError("");

    try {
      const learningObjectives = parseObjectives(
        activeLessonDraft.learningObjectives,
      );
      const estimatedTimeMinutes = activeLessonDraft.estimatedTimeMinutes
        ? Number(activeLessonDraft.estimatedTimeMinutes)
        : null;
      const savedLesson = await updateLessonApi(
        createdCourse.id,
        activeLesson.id,
        {
          title,
          description,
          learningObjectives,
          estimatedTimeMinutes: Number.isFinite(estimatedTimeMinutes)
            ? estimatedTimeMinutes
            : null,
        },
      );

      setLessons((prev) =>
        prev.map((lesson) =>
          lesson.id === activeLesson.id
            ? {
                ...lesson,
                ...savedLesson,
                title,
                description,
                summary: description,
                learningObjectives,
                learning_objectives: learningObjectives,
                estimated_time_minutes: Number.isFinite(estimatedTimeMinutes)
                  ? estimatedTimeMinutes
                  : null,
              }
            : lesson,
        ),
      );
    } catch (error) {
      setLessonMetaError(
        getApiErrorMessage(error, "Не удалось сохранить метаданные урока."),
      );
    } finally {
      setIsSavingLessonMeta(false);
    }
  };

  const saveLessonContent = async (changes = null) => {
    if (!activeLesson) {
      return;
    }

    setIsSavingLessonContent(true);
    setLessonContentError("");

    try {
      const nextMarkdown = changes?.markdown ?? lessonContentDraft;
      const contentBlocks =
        changes?.contentBlocks || markdownToTextContentBlocks(nextMarkdown);
      const savedLesson = await updateLessonContentBlocks(
        activeLesson.id,
        contentBlocks,
      );

      setLessonContentDraft(nextMarkdown);
      setLessons((prev) =>
        prev.map((lesson) =>
          lesson.id === activeLesson.id
            ? {
                ...lesson,
                ...savedLesson,
                contentBlocks,
                content_blocks: contentBlocks,
                markdown: nextMarkdown,
                content: nextMarkdown,
              }
            : lesson,
        ),
      );
    } catch (error) {
      setLessonContentError(
        getApiErrorMessage(error, "Не удалось сохранить контент урока."),
      );
    } finally {
      setIsSavingLessonContent(false);
    }
  };

  const openStructureEditor = (type, item) => {
    setActiveLessonId(null);
    setEditingStructure({ type, id: item.id });
    setStructureDraft({
      title: item.title || "",
      description: item.description || item.summary || "",
      learningObjectives: (
        item.learningObjectives ||
        item.learning_objectives ||
        []
      ).join("\n"),
      estimatedTimeMinutes:
        item.estimated_time_minutes || item.estimatedTimeMinutes || "",
    });
    setStructureEditError("");
  };

  const closeStructureEditor = () => {
    setEditingStructure(null);
    setStructureEditError("");
  };

  const returnToBlocks = () => {
    setActiveLessonId(null);
    setEditingStructure(null);
  };

  const updateStructureDraft = (field, value) => {
    setStructureDraft((prev) => ({ ...prev, [field]: value }));
  };

  const submitStructureEditor = async (event) => {
    event.preventDefault();

    if (!editingStructure || !createdCourse?.id) {
      return;
    }

    const title = structureDraft.title.trim();
    const description = structureDraft.description.trim();

    if (!title || !description) {
      setStructureEditError("Заполните название и описание.");
      return;
    }

    setIsSavingStructure(true);
    setStructureEditError("");

    try {
      const learningObjectives = parseObjectives(
        structureDraft.learningObjectives,
      );

      if (editingStructure.type === "module") {
        const savedModule = await updateModuleApi(
          createdCourse.id,
          editingStructure.id,
          {
            title,
            description,
            learningObjectives,
          },
        );

        setModules((prev) =>
          prev.map((module) =>
            module.id === editingStructure.id
              ? {
                  ...module,
                  ...savedModule,
                  title,
                  description,
                  learningObjectives,
                  learning_objectives: learningObjectives,
                  lessonIds: module.lessonIds,
                }
              : module,
          ),
        );
      } else {
        const estimatedTimeMinutes = structureDraft.estimatedTimeMinutes
          ? Number(structureDraft.estimatedTimeMinutes)
          : null;
        const savedLesson = await updateLessonApi(
          createdCourse.id,
          editingStructure.id,
          {
            title,
            description,
            learningObjectives,
            estimatedTimeMinutes: Number.isFinite(estimatedTimeMinutes)
              ? estimatedTimeMinutes
              : null,
          },
        );

        setLessons((prev) =>
          prev.map((lesson) =>
            lesson.id === editingStructure.id
              ? {
                  ...lesson,
                  ...savedLesson,
                  title,
                  description,
                  summary: description,
                  learningObjectives,
                  learning_objectives: learningObjectives,
                  estimated_time_minutes: Number.isFinite(estimatedTimeMinutes)
                    ? estimatedTimeMinutes
                    : null,
                }
              : lesson,
          ),
        );
      }

      closeStructureEditor();
    } catch (error) {
      setStructureEditError(
        getApiErrorMessage(error, "Не удалось сохранить изменения."),
      );
    } finally {
      setIsSavingStructure(false);
    }
  };

  const updateCourseDraft = (field, value) => {
    setCourseDraft((prev) => ({ ...prev, [field]: value }));
  };

  const parseTags = (value) =>
    value
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);

  const submitCourseDraft = async (event) => {
    event.preventDefault();

    if (isCreatingCourse) {
      return;
    }

    const title = courseDraft.title.trim();
    const description = courseDraft.description.trim();
    const tags = parseTags(courseDraft.tags);

    if (!title || !description) {
      setCourseCreateError("Заполните название и описание курса.");
      return;
    }

    setIsCreatingCourse(true);
    setCourseCreateError("");

    try {
      if (hasCreatedCourse) {
        const updatedCourse = await updateCourseApi(createdCourse.id, {
          title,
          description,
          difficulty: courseDraft.difficulty,
          tags,
        });
        setCreatedCourse((current) => ({
          ...current,
          ...(updatedCourse || {}),
          id: current.id,
          title,
          description,
          difficulty: courseDraft.difficulty,
          tags,
        }));
        setIsCourseFormOpen(false);
        return;
      }

      const course = await createCourseApi({
        title,
        description,
        difficulty: courseDraft.difficulty,
        tags,
      });
      setCreatedCourse(course);
      setIsCourseFormOpen(false);
    } catch (error) {
      setCourseCreateError(
        getApiErrorMessage(
          error,
          hasCreatedCourse
            ? "Не удалось обновить курс."
            : "Не удалось создать курс.",
        ),
      );
    } finally {
      setIsCreatingCourse(false);
    }
  };

  const createCourse = async () => {
    if (modules.length === 0 || !createdCourse?.id || isFinishing) {
      return;
    }

    setIsFinishing(true);
    setFinishError("");

    try {
      await onCreateCourse({ courseId: createdCourse.id });
      clearManualBuilderDraft();
    } catch (error) {
      setFinishError(
        getApiErrorMessage(
          error,
          "Курс создан, но не удалось открыть страницу редактирования.",
        ),
      );
      setIsFinishing(false);
    }
  };

  const renderDropzone = (compact = false) => (
    <>
      <button
        type="button"
        className={`manual-dropzone ${
          compact ? "manual-dropzone-compact" : "manual-dropzone-start"
        } ${isDragging ? "is-dragging" : ""}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
      >
        <span>+</span>
        <strong>
          {compact ? "Добавить ещё материал" : "Перетащите материалы сюда"}
        </strong>
        <small>
          {compact
            ? "Можно добавить несколько материалов"
            : "или нажмите, чтобы выбрать файлы"}
        </small>
        {!compact && (
          <small>После загрузки материалы превращаются в блоки.</small>
        )}
      </button>

      <input
        ref={fileInputRef}
        className="manual-file-input"
        type="file"
        multiple
        onChange={(event) => {
          handleFiles(event.target.files);
          event.target.value = "";
        }}
      />
    </>
  );

  const renderBlockAiEditor = (block) => (
    <aside className="lesson-ai-editor">
      <div className="lesson-ai-editor-head">
        <span>ИИ-редактор</span>
        <button
          type="button"
          onClick={closeBlockAiEditor}
          aria-label="Свернуть ИИ-редактор"
          title="Свернуть ИИ-редактор"
        >
          −
        </button>
      </div>

      <div
        className="lesson-ai-messages"
        ref={aiMessagesRef}
        aria-live="polite"
        aria-busy={isAiSending}
      >
        {(aiConversation?.messages || []).length === 0 && (
          <div className="lesson-ai-message is-assistant">
            <p>
              Опишите, что нужно изменить. Я подготовлю правку, а история
              диалога останется здесь.
            </p>
          </div>
        )}
        {(aiConversation?.messages || []).map((message) => (
          <div
            key={message.id}
            className={`lesson-ai-message is-${message.role}`}
          >
            <p>{message.text}</p>
            {message.role === "user" && (
              <span className="chat-message-status">✓ Отправлено</span>
            )}
          </div>
        ))}
        {isAiSending && (
          <div className="lesson-ai-message is-assistant is-thinking">
            <span className="chat-thinking-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <span>ИИ получил сообщение и готовит правку…</span>
          </div>
        )}
      </div>

      {aiError && <p className="lesson-ai-error">{aiError}</p>}

      <div className="lesson-ai-composer manual-ai-composer">
        <textarea
          value={aiInput}
          onChange={(event) => setAiInput(event.target.value)}
          placeholder={
            isAiSending
              ? "Можно написать следующее сообщение — отправка после ответа"
              : "Напишите, что нужно изменить"
          }
          maxLength={10_000}
          disabled={!createdCourse?.id}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing) {
              return;
            }
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              askBlockAi();
            }
          }}
        />
        <button
          type="button"
          className="lesson-ai-send"
          onClick={askBlockAi}
          disabled={isAiSending || !createdCourse?.id || !aiInput.trim()}
          aria-label="Отправить сообщение"
          title="Отправить"
        >
          ↑
        </button>
      </div>
    </aside>
  );

  return (
    <section
      className={`container section manual-builder-view ${hasBlocks ? "has-sidebar" : ""}`}
    >
      <SectionTop
        label="Конструктор"
        title="Создать курс самостоятельно"
        text={
          hasCreatedCourse && !isCourseFormOpen
            ? "Курс создан. Теперь загрузите материалы и соберите модули с уроками."
            : "Заполните или проверьте карточку курса. После сохранения станет доступна загрузка файлов."
        }
      />

      <div className="manual-builder-flow">
        {/* =====================================================
            ИНСТРУКЦИЯ
        ====================================================== */}
        <article className="glass-card manual-instruction-card">
          <div className="manual-instruction-icon">i</div>
          <div>
            <span className="manual-instruction-label">Как создать курс</span>
            <h3>Сначала создайте курс, затем наполните его материалами</h3>
            <ol>
              <li>Заполните название, описание, сложность и теги курса.</li>
              <li>
                После успешного создания загрузите лекции, конспекты или
                документы — они превратятся в готовые блоки.
              </li>
              <li>
                Отметьте нужные блоки, объедините их в уроки и сгруппируйте
                уроки в модули. Слева будет отображаться дерево курса.
              </li>
            </ol>
          </div>
        </article>

        {(!hasCreatedCourse || isCourseFormOpen) && (
          <article className="glass-card manual-section-card manual-course-create-card">
            <div className="manual-card-head">
              <div>
                <span>Шаг 1</span>
                <h3>Карточка курса</h3>
              </div>
              <div className="manual-card-head-actions">
                <strong>
                  {hasCreatedCourse
                    ? "PUT /course/edit"
                    : "POST /course/create"}
                </strong>
                {hasCreatedCourse && (
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => {
                      setCourseCreateError("");
                      setIsCourseFormOpen(false);
                    }}
                    disabled={isCreatingCourse}
                  >
                    Вернуться к материалам
                  </button>
                )}
              </div>
            </div>

            <form
              className="manual-course-create-form"
              onSubmit={submitCourseDraft}
            >
              <label className="course-editor-field course-editor-field-wide">
                <span>Название курса</span>
                <input
                  value={courseDraft.title}
                  onChange={(event) =>
                    updateCourseDraft("title", event.target.value)
                  }
                  placeholder="Например: Основы Python для аналитиков"
                  required
                />
              </label>

              <label className="course-editor-field course-editor-field-wide">
                <span>Описание</span>
                <textarea
                  value={courseDraft.description}
                  onChange={(event) =>
                    updateCourseDraft("description", event.target.value)
                  }
                  placeholder="Кратко опишите, чему научится студент"
                  required
                />
              </label>

              <div className="manual-course-create-grid">
                <label className="course-editor-field">
                  <span>Сложность</span>
                  <select
                    value={courseDraft.difficulty}
                    onChange={(event) =>
                      updateCourseDraft("difficulty", event.target.value)
                    }
                  >
                    {DIFFICULTY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="course-editor-field">
                  <span>Теги</span>
                  <input
                    value={courseDraft.tags}
                    onChange={(event) =>
                      updateCourseDraft("tags", event.target.value)
                    }
                    placeholder="python, backend, junior"
                  />
                </label>
              </div>

              {courseCreateError && (
                <p className="manual-course-create-error">
                  {courseCreateError}
                </p>
              )}

              <button
                type="submit"
                className="btn btn-solid manual-course-create-submit"
                disabled={isCreatingCourse}
              >
                {isCreatingCourse
                  ? hasCreatedCourse
                    ? "Сохраняем курс..."
                    : "Создаём курс..."
                  : hasCreatedCourse
                    ? "Сохранить и вернуться к материалам"
                    : "Создать курс"}
              </button>
            </form>
          </article>
        )}

        {hasCreatedCourse && !isCourseFormOpen && (
          <div className="manual-builder-shell">
            <div className="manual-builder-course-toolbar glass-card">
              <div>
                <span>Карточка курса</span>
                <strong>{createdCourse.title}</strong>
              </div>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => {
                  setCourseCreateError("");
                  setIsCourseFormOpen(true);
                }}
              >
                Вернуться к данным курса
              </button>
            </div>
            <div
              className={`manual-builder-layout ${hasBlocks ? "has-sidebar" : ""}`}
            >
              {hasBlocks && (
                <aside className="manual-sidebar">
                  <aside
                    className="course-nav-tree manual-course-tree"
                    aria-label="Дерево курса"
                  >
                    <div className="course-nav-tree-head">
                      <strong>{createdCourse.title}</strong>
                      <span>
                        {modules.length} модулей · {lessons.length} уроков
                      </span>
                    </div>

                    {hasModules && (
                      <button
                        type="button"
                        className="btn btn-solid manual-tree-finish-btn"
                        onClick={createCourse}
                        disabled={isFinishing}
                      >
                        {isFinishing ? "Открываем редактор..." : "Завершить"}
                      </button>
                    )}

                    {finishError && (
                      <p className="manual-course-create-error">
                        {finishError}
                      </p>
                    )}

                    {treeActionError && (
                      <p className="manual-course-create-error">
                        {treeActionError}
                      </p>
                    )}

                    {courseTreeModules.length > 0 ? (
                      <ul className="course-nav-block-list manual-tree-list">
                        {courseTreeModules
                          .filter(
                            (module) => !isModuleFormOpen || !module.isDraft,
                          )
                          .map((module, moduleIndex) => {
                            const moduleLessons = (module.lessonIds || [])
                              .map((lessonId) =>
                                lessons.find(
                                  (lesson) => lesson.id === lessonId,
                                ),
                              )
                              .filter(Boolean);

                            return (
                              <li
                                className={`course-nav-block ${
                                  dragOverModuleId === module.id
                                    ? "is-drag-over"
                                    : ""
                                }`}
                                key={module.id}
                              >
                                <div
                                  className={`manual-tree-module-row ${
                                    module.isDraft ? "is-static" : ""
                                  } ${
                                    dragOverModuleId === module.id
                                      ? "is-lesson-drop-target"
                                      : ""
                                  } ${
                                    draggedModuleId === module.id
                                      ? "is-dragging"
                                      : ""
                                  }`}
                                  draggable={
                                    !module.isDraft && !isReorderingModules
                                  }
                                  onDragStart={(event) => {
                                    if (module.isDraft) return;
                                    event.dataTransfer.effectAllowed = "move";
                                    event.dataTransfer.setData(
                                      "text/plain",
                                      module.id,
                                    );
                                    setDraggedModuleId(module.id);
                                  }}
                                  onDragOver={(event) => {
                                    if (module.isDraft) return;
                                    const canAcceptLesson =
                                      draggedLessonId &&
                                      !assignedLessonIds.has(draggedLessonId);
                                    if (!draggedModuleId && !canAcceptLesson) {
                                      return;
                                    }
                                    event.preventDefault();
                                    event.dataTransfer.dropEffect = "move";
                                    setDragOverModuleId(module.id);
                                  }}
                                  onDrop={(event) => {
                                    event.preventDefault();
                                    if (module.isDraft) return;

                                    if (
                                      draggedLessonId &&
                                      !assignedLessonIds.has(draggedLessonId)
                                    ) {
                                      moveUnassignedLessonToModule(
                                        draggedLessonId,
                                        module,
                                      );
                                      return;
                                    }

                                    reorderModules(module.id);
                                  }}
                                  onDragEnd={() => {
                                    setDraggedModuleId(null);
                                    setDragOverModuleId(null);
                                  }}
                                >
                                  <button
                                    type="button"
                                    className={`course-nav-block-btn manual-course-tree-module ${
                                      module.isDraft ? "is-draft" : ""
                                    }`}
                                    onClick={() =>
                                      !module.isDraft &&
                                      openStructureEditor("module", module)
                                    }
                                    disabled={module.isDraft}
                                  >
                                    {!module.isDraft && (
                                      <span>{moduleIndex + 1}</span>
                                    )}
                                    <strong>{module.title}</strong>
                                  </button>
                                  {!module.isDraft && (
                                    <button
                                      type="button"
                                      className="manual-tree-delete-btn"
                                      onClick={() => deleteCourseModule(module)}
                                      disabled={
                                        deletingTreeItemId === module.id
                                      }
                                      aria-label={`Удалить модуль ${module.title}`}
                                      title="Удалить модуль"
                                    >
                                      ×
                                    </button>
                                  )}
                                </div>
                                <ul className="course-nav-item-list manual-tree-lesson-list">
                                  {moduleLessons.map((lesson, lessonIndex) => {
                                    const canSelectLesson =
                                      module.isDraft ||
                                      modules.some(
                                        (item) => item.id !== module.id,
                                      );

                                    return (
                                      <li key={lesson.id}>
                                        <div
                                          className={`course-nav-item-btn manual-course-tree-lesson ${
                                            selectedLessonIds.includes(
                                              lesson.id,
                                            )
                                              ? "is-active"
                                              : ""
                                          } ${activeLessonId === lesson.id ? "is-open" : ""} ${
                                            dragOverLessonId === lesson.id
                                              ? "is-drag-over"
                                              : ""
                                          } ${
                                            draggedLessonId === lesson.id
                                              ? "is-dragging"
                                              : ""
                                          }`}
                                          draggable={
                                            !isReorderingLessons &&
                                            !isMovingDraggedLesson
                                          }
                                          onDragStart={(event) => {
                                            event.stopPropagation();
                                            event.dataTransfer.effectAllowed =
                                              "move";
                                            event.dataTransfer.setData(
                                              "text/plain",
                                              lesson.id,
                                            );
                                            setDraggedLessonId(lesson.id);
                                          }}
                                          onDragOver={(event) => {
                                            if (!draggedLessonId) return;
                                            event.preventDefault();
                                            event.stopPropagation();
                                            event.dataTransfer.dropEffect =
                                              "move";

                                            if (
                                              !module.isDraft &&
                                              !assignedLessonIds.has(
                                                draggedLessonId,
                                              )
                                            ) {
                                              setDragOverModuleId(module.id);
                                              setDragOverLessonId(null);
                                              return;
                                            }

                                            setDragOverLessonId(lesson.id);
                                          }}
                                          onDrop={(event) => {
                                            event.preventDefault();
                                            event.stopPropagation();

                                            if (
                                              !module.isDraft &&
                                              draggedLessonId &&
                                              !assignedLessonIds.has(
                                                draggedLessonId,
                                              )
                                            ) {
                                              moveUnassignedLessonToModule(
                                                draggedLessonId,
                                                module,
                                              );
                                              return;
                                            }

                                            reorderLessons(module, lesson.id);
                                          }}
                                          onDragEnd={() => {
                                            setDraggedLessonId(null);
                                            setDragOverLessonId(null);
                                            setDragOverModuleId(null);
                                          }}
                                          title="Перетащите, чтобы изменить порядок уроков"
                                        >
                                          <input
                                            type="checkbox"
                                            aria-label={`Выбрать ${lesson.title}`}
                                            checked={selectedLessonIds.includes(
                                              lesson.id,
                                            )}
                                            onChange={() =>
                                              toggleLessonSelection(lesson.id)
                                            }
                                            disabled={
                                              !canSelectLesson ||
                                              isReorderingLessons
                                            }
                                          />
                                          <button
                                            type="button"
                                            className={`manual-tree-lesson-open ${
                                              module.isDraft ? "is-draft" : ""
                                            }`}
                                            onClick={() =>
                                              openLessonContent(lesson)
                                            }
                                          >
                                            {!module.isDraft && (
                                              <span className="course-nav-item-number">
                                                {moduleIndex + 1}.
                                                {lessonIndex + 1}
                                              </span>
                                            )}
                                            <span className="course-nav-item-title">
                                              {lesson.title}
                                            </span>
                                          </button>
                                        </div>
                                      </li>
                                    );
                                  })}
                                </ul>
                              </li>
                            );
                          })}
                      </ul>
                    ) : (
                      <p className="manual-course-tree-empty">
                        Уроки появятся здесь после объединения блоков.
                      </p>
                    )}
                  </aside>

                  {availableBlocks.length > 0 && (
                    <div className="manual-selection-toolbar manual-block-merge-toolbar">
                      <span>{selectedBlocks.length} блоков выбрано</span>
                      <button
                        type="button"
                        className="btn btn-solid"
                        onClick={mergeSelectedBlocksIntoLesson}
                        disabled={!canCreateLesson}
                      >
                        {isCreatingLesson
                          ? "Сохраняем урок..."
                          : "Объединить в урок"}
                      </button>
                      {lessonCreateError && (
                        <p className="manual-merge-error">
                          {lessonCreateError}
                        </p>
                      )}
                    </div>
                  )}

                  {selectedLessonIds.length > 0 && !isModuleFormOpen && (
                    <div className="manual-selection-toolbar manual-block-merge-toolbar manual-tree-toolbar">
                      <span>{selectedLessonIds.length} уроков выбрано</span>

                      {selectedLessonsAreUnassigned && (
                        <button
                          type="button"
                          className="btn btn-solid"
                          onClick={openModuleForm}
                          disabled={!canCreateModule}
                        >
                          Объединить в модуль
                        </button>
                      )}

                      {selectedLessonsAreAssigned &&
                        transferTargetModules.length > 0 && (
                          <>
                            <label className="manual-module-transfer-target">
                              <span>Перенести в</span>
                              <select
                                value={selectedTransferTargetId}
                                onChange={(event) =>
                                  setTransferTargetModuleId(event.target.value)
                                }
                              >
                                {transferTargetModules.map((module) => (
                                  <option key={module.id} value={module.id}>
                                    {module.title}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <button
                              type="button"
                              className="btn btn-solid"
                              onClick={moveSelectedLessonsToModule}
                              disabled={!canMoveLessons}
                            >
                              {isMovingLessons
                                ? "Переносим уроки..."
                                : "Перенести в модуль"}
                            </button>
                          </>
                        )}

                      {selectedLessonsAreAssigned &&
                        transferTargetModules.length === 0 && (
                          <p className="manual-merge-error">
                            Для переноса нужен другой модуль.
                          </p>
                        )}

                      {selectedLessonsAreAssigned && moduleCreateError && (
                        <p className="manual-merge-error">
                          {moduleCreateError}
                        </p>
                      )}
                    </div>
                  )}

                  {isModuleFormOpen && selectedLessonsAreUnassigned && (
                    <form
                      className="manual-module-form manual-tree-form"
                      onSubmit={submitModuleDraft}
                    >
                      <label className="course-editor-field course-editor-field-wide">
                        <span>Название модуля</span>
                        <input
                          value={moduleDraft.title}
                          onChange={(event) =>
                            updateModuleDraft("title", event.target.value)
                          }
                          placeholder="Например: Основы синтаксиса"
                          required
                        />
                      </label>
                      <label className="course-editor-field course-editor-field-wide">
                        <span>Описание модуля</span>
                        <textarea
                          value={moduleDraft.description}
                          onChange={(event) =>
                            updateModuleDraft("description", event.target.value)
                          }
                          placeholder="Кратко опишите содержание модуля"
                          required
                        />
                      </label>
                      <label className="course-editor-field course-editor-field-wide">
                        <span>Цели обучения</span>
                        <textarea
                          value={moduleDraft.learningObjectives}
                          onChange={(event) =>
                            updateModuleDraft(
                              "learningObjectives",
                              event.target.value,
                            )
                          }
                          placeholder="Каждая цель с новой строки"
                        />
                      </label>
                      {moduleCreateError && (
                        <p className="manual-course-create-error">
                          {moduleCreateError}
                        </p>
                      )}
                      <div className="manual-module-form-actions">
                        <button
                          type="button"
                          className="btn btn-outline"
                          onClick={() => setIsModuleFormOpen(false)}
                          disabled={isCreatingModule}
                        >
                          Отмена
                        </button>
                        <button
                          type="submit"
                          className="btn btn-solid"
                          disabled={isCreatingModule}
                        >
                          {isCreatingModule
                            ? "Сохраняем..."
                            : "Сохранить модуль"}
                        </button>
                      </div>
                    </form>
                  )}

                  <div className="manual-sidebar-dropzone">
                    {renderDropzone(true)}
                  </div>
                </aside>
              )}

              <main className="manual-content">
                {/* =====================================================
            МАТЕРИАЛЫ → БЛОКИ
        ====================================================== */}
                {!hasBlocks && (
                  <article className="glass-card manual-start-card">
                    {renderDropzone()}
                  </article>
                )}

                {activeModule && (
                  <article className="glass-card manual-section-card manual-active-module-card">
                    <div className="manual-card-head">
                      <div>
                        <span>Модуль</span>
                        <h3>{activeModule.title}</h3>
                      </div>
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={returnToBlocks}
                      >
                        Вернуться к блокам
                      </button>
                    </div>

                    <form
                      className="course-editor-panel block-editor-panel"
                      onSubmit={submitStructureEditor}
                    >
                      <div className="course-editor-grid">
                        <label className="course-editor-field">
                          <span>Название модуля</span>
                          <input
                            value={structureDraft.title}
                            onChange={(event) =>
                              updateStructureDraft("title", event.target.value)
                            }
                            required
                          />
                        </label>
                        <label className="course-editor-field">
                          <span>Позиция</span>
                          <input value={activeModule.order || ""} disabled />
                        </label>
                        <label className="course-editor-field course-editor-field-wide">
                          <span>Описание</span>
                          <textarea
                            value={structureDraft.description}
                            onChange={(event) =>
                              updateStructureDraft(
                                "description",
                                event.target.value,
                              )
                            }
                            required
                          />
                        </label>
                        <label className="course-editor-field course-editor-field-wide">
                          <span>Цели обучения</span>
                          <textarea
                            value={structureDraft.learningObjectives}
                            onChange={(event) =>
                              updateStructureDraft(
                                "learningObjectives",
                                event.target.value,
                              )
                            }
                            placeholder="Каждая цель с новой строки"
                          />
                        </label>
                      </div>

                      {structureEditError && (
                        <p className="manual-course-create-error">
                          {structureEditError}
                        </p>
                      )}

                      <div className="course-editor-actions">
                        <button
                          type="button"
                          className="btn btn-outline"
                          onClick={returnToBlocks}
                          disabled={isSavingStructure}
                        >
                          Отмена
                        </button>
                        <button
                          type="submit"
                          className="btn btn-solid"
                          disabled={isSavingStructure}
                        >
                          {isSavingStructure
                            ? "Сохраняем..."
                            : "Сохранить модуль"}
                        </button>
                      </div>
                    </form>
                  </article>
                )}

                {activeLesson && (
                  <article className="glass-card lesson-main-card is-editing manual-active-lesson-card">
                    <div className="lesson-scroll-frame">
                      <div className="manual-card-head">
                        <div>
                          <span>Урок</span>
                          <h3>{activeLesson.title}</h3>
                        </div>
                        <div className="manual-card-head-actions">
                          <button
                            type="button"
                            className="btn btn-outline manual-lesson-delete-btn"
                            onClick={() => deleteCourseLesson(activeLesson)}
                            disabled={deletingTreeItemId === activeLesson.id}
                          >
                            {deletingTreeItemId === activeLesson.id
                              ? "Удаляем урок..."
                              : "Удалить урок"}
                          </button>
                          <button
                            type="button"
                            className="btn btn-outline"
                            onClick={returnToBlocks}
                          >
                            Вернуться к блокам
                          </button>
                        </div>
                      </div>

                      <div className="course-editor-panel lesson-editor-panel">
                        <div className="course-editor-grid">
                          <label className="course-editor-field">
                            <span>Название урока</span>
                            <input
                              value={activeLessonDraft.title}
                              onChange={(event) =>
                                updateActiveLessonDraft(
                                  "title",
                                  event.target.value,
                                )
                              }
                            />
                          </label>
                          <label className="course-editor-field">
                            <span>Длительность</span>
                            <input
                              type="number"
                              min="0"
                              value={activeLessonDraft.estimatedTimeMinutes}
                              onChange={(event) =>
                                updateActiveLessonDraft(
                                  "estimatedTimeMinutes",
                                  event.target.value,
                                )
                              }
                            />
                          </label>
                          <label className="course-editor-field course-editor-field-wide">
                            <span>Краткое описание</span>
                            <textarea
                              value={activeLessonDraft.description}
                              onChange={(event) =>
                                updateActiveLessonDraft(
                                  "description",
                                  event.target.value,
                                )
                              }
                            />
                          </label>
                          <label className="course-editor-field course-editor-field-wide">
                            <span>Цели обучения</span>
                            <textarea
                              value={activeLessonDraft.learningObjectives}
                              onChange={(event) =>
                                updateActiveLessonDraft(
                                  "learningObjectives",
                                  event.target.value,
                                )
                              }
                              placeholder="Каждая цель с новой строки"
                            />
                          </label>
                        </div>

                        {lessonMetaError && (
                          <p className="manual-course-create-error">
                            {lessonMetaError}
                          </p>
                        )}

                        <div className="course-editor-actions">
                          <button
                            type="button"
                            className="btn btn-outline"
                            onClick={saveLessonMetadata}
                            disabled={isSavingLessonMeta}
                          >
                            {isSavingLessonMeta
                              ? "Сохраняем метаданные..."
                              : "Сохранить метаданные"}
                          </button>
                        </div>

                        <LessonContentEditor
                          courseId={createdCourse.id}
                          lesson={{
                            ...activeLesson,
                            markdown: lessonContentDraft,
                            contentBlocks:
                              activeLesson.contentBlocks ||
                              activeLesson.content_blocks ||
                              markdownToTextContentBlocks(lessonContentDraft),
                          }}
                          onChange={(changes) => saveLessonContent(changes)}
                          contentLabel="Теория"
                          blocksLabel="Блоки урока"
                          showInsertControls={false}
                        />

                        {lessonContentError && (
                          <p className="manual-course-create-error">
                            {lessonContentError}
                          </p>
                        )}
                        {isSavingLessonContent && (
                          <p className="course-viewer-muted">
                            Сохраняем content blocks...
                          </p>
                        )}
                      </div>
                    </div>
                  </article>
                )}

                {!activeLesson && !activeModule && hasBlocks && (
                  <article className="glass-card manual-section-card">
                    <div className="manual-card-head">
                      <div>
                        <span>Шаг 1</span>
                        <h3>Блоки</h3>
                      </div>
                      <strong>{readyBlocks.length} готово</strong>
                    </div>

                    <div className="manual-blocks-list">
                      {availableBlocks.map((block) => (
                        <div
                          className={`lesson-editor-block-row manual-block-preview-row ${
                            chatBlockId === block.id ? "has-ai" : ""
                          }`}
                          key={block.id}
                        >
                          <article
                            className={`manual-block-preview-card ${
                              block.selected ? "is-selected" : ""
                            } ${block.status === "error" ? "has-error" : ""}`}
                            id={block.id}
                          >
                            <div className="manual-block-preview-head">
                              <label className="manual-block-select">
                                <input
                                  type="checkbox"
                                  checked={block.selected}
                                  disabled={block.status !== "ready"}
                                  onChange={() =>
                                    toggleBlockSelection(block.id)
                                  }
                                />
                                <strong>Блок {block.blockNumber}</strong>
                              </label>
                              <div className="manual-block-head-side">
                                <span className="manual-block-status">
                                  {block.status === "uploading" &&
                                    "Обработка материала..."}
                                  {block.status === "ready" &&
                                    "Материал обработан"}
                                  {block.status === "error" && block.error}
                                </span>
                                <div className="manual-block-actions">
                                  {block.status === "ready" && (
                                    <>
                                      <button
                                        type="button"
                                        className={`btn btn-outline ${
                                          editingBlockId === block.id
                                            ? "is-active"
                                            : ""
                                        }`}
                                        onClick={() =>
                                          toggleBlockEditing(block.id)
                                        }
                                      >
                                        {editingBlockId === block.id
                                          ? "Готово"
                                          : "Редактировать"}
                                      </button>
                                      <button
                                        type="button"
                                        className={`btn btn-outline ${
                                          chatBlockId === block.id
                                            ? "is-active"
                                            : ""
                                        }`}
                                        onClick={() =>
                                          toggleBlockChat(block.id)
                                        }
                                      >
                                        ИИ-редактор
                                      </button>
                                    </>
                                  )}
                                  <button
                                    type="button"
                                    className="btn btn-outline manual-delete-action"
                                    onClick={() =>
                                      deleteAvailableBlock(block.id)
                                    }
                                  >
                                    Удалить блок
                                  </button>
                                </div>
                              </div>
                            </div>

                            {block.status === "uploading" && (
                              <div className="manual-preview-empty">
                                <strong>Материал обрабатывается...</strong>
                                <p>Ожидаем ответ backend.</p>
                              </div>
                            )}

                            {block.status === "error" && (
                              <div className="manual-preview-empty">
                                <strong>Не удалось обработать материал</strong>
                                <p>{block.error}</p>
                              </div>
                            )}

                            {block.status === "ready" && block.proposal ? (
                              <div className="lesson-block-proposal">
                                <div className="lesson-block-proposal-head">
                                  <span>Предложено ИИ</span>
                                  <div className="lesson-block-proposal-actions">
                                    <button
                                      type="button"
                                      className="btn btn-solid"
                                      onClick={() =>
                                        applyBlockProposal(block.id)
                                      }
                                    >
                                      Применить
                                    </button>
                                    <button
                                      type="button"
                                      className="btn btn-outline"
                                      onClick={() =>
                                        rejectBlockProposal(block.id)
                                      }
                                    >
                                      Не применять
                                    </button>
                                  </div>
                                </div>
                                <div className="lesson-markdown lesson-proposal-preview">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {block.proposal}
                                  </ReactMarkdown>
                                </div>
                              </div>
                            ) : (
                              block.status === "ready" &&
                              (editingBlockId === block.id ? (
                                <textarea
                                  className="manual-block-editor"
                                  value={block.markdown}
                                  onChange={(event) =>
                                    updateBlockMarkdown(
                                      block.id,
                                      event.target.value,
                                    )
                                  }
                                />
                              ) : (
                                <div className="lesson-markdown manual-lesson-preview">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {block.markdown}
                                  </ReactMarkdown>
                                </div>
                              ))
                            )}
                          </article>
                          {chatBlockId === block.id &&
                            renderBlockAiEditor(block)}
                        </div>
                      ))}
                      {availableBlocks.length === 0 && (
                        <div className="manual-preview-empty">
                          <strong>
                            Все загруженные блоки уже объединены в уроки.
                          </strong>
                          <p>
                            Добавьте ещё материалы, чтобы создать новый урок.
                          </p>
                        </div>
                      )}
                    </div>
                  </article>
                )}
              </main>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
