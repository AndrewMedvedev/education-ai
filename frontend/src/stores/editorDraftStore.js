import { create } from "zustand";

/**
 * Несохранённые правки модулей и уроков в редакторе курса.
 * Правки применяются к интерфейсу сразу, а на backend уходят только после
 * подтверждения в окне «Сохранить изменения».
 *
 * edits[key] = {
 *   key, kind: "module" | "lesson", courseId, entityId, label,
 *   original: { field: значение до правок },
 *   changes: { field: новое значение },
 *   error: string,
 * }
 */

// Служебные поля, которые меняются вместе с контентом урока и не показываются отдельно.
const DERIVED_FIELDS = new Set(["markdown", "content", "content_blocks"]);

export const draftKey = (kind, entityId) => `${kind}:${entityId}`;

function isSameValue(left, right) {
  if (left === right) return true;
  try {
    return JSON.stringify(left ?? null) === JSON.stringify(right ?? null);
  } catch {
    return false;
  }
}

function hasVisibleChanges(edit) {
  return Object.keys(edit.changes).some((field) => !DERIVED_FIELDS.has(field));
}

export const useEditorDraftStore = create((set, get) => ({
  edits: {},
  // Растёт при отмене правок: редакторы с внутренним состоянием пересоздаются.
  revision: 0,

  bumpRevision: () => set((state) => ({ revision: state.revision + 1 })),

  recordEdit: ({ kind, courseId, entityId, label, entity, changes }) => {
    if (!kind || !entityId || !changes) return;
    set((state) => {
      const key = draftKey(kind, entityId);
      const current = state.edits[key] || {
        key,
        kind,
        courseId,
        entityId,
        label: label || "",
        original: {},
        changes: {},
        error: "",
      };
      const original = { ...current.original };
      const nextChanges = { ...current.changes };

      Object.entries(changes).forEach(([field, value]) => {
        if (!(field in original)) {
          original[field] = entity ? entity[field] : undefined;
        }
        if (isSameValue(original[field], value)) {
          delete nextChanges[field];
        } else {
          nextChanges[field] = value;
        }
      });

      const edits = { ...state.edits };
      const nextEdit = {
        ...current,
        courseId: courseId || current.courseId,
        label: label || current.label,
        original,
        changes: nextChanges,
        error: "",
      };
      if (hasVisibleChanges(nextEdit)) {
        edits[key] = nextEdit;
      } else {
        delete edits[key];
      }
      return { edits };
    });
  },

  setEditError: (key, error) =>
    set((state) =>
      state.edits[key]
        ? { edits: { ...state.edits, [key]: { ...state.edits[key], error } } }
        : {},
    ),

  removeEdit: (key) =>
    set((state) => {
      if (!state.edits[key]) return {};
      const edits = { ...state.edits };
      delete edits[key];
      return { edits };
    }),

  removeEntity: (kind, entityId) => get().removeEdit(draftKey(kind, entityId)),

  clearCourse: (courseId) =>
    set((state) => ({
      edits: Object.fromEntries(
        Object.entries(state.edits).filter(
          ([, edit]) => edit.courseId !== courseId,
        ),
      ),
    })),

  getCourseEdits: (courseId) =>
    Object.values(get().edits).filter((edit) => edit.courseId === courseId),
}));

export const isDerivedDraftField = (field) => DERIVED_FIELDS.has(field);
