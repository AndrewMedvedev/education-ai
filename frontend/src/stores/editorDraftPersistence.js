// No browser or Zustand dependencies: the same state machine is tested with node:test.
export const DRAFT_STORAGE_VERSION = 1;
export const DRAFT_STORAGE_PREFIX = "aicolab-editor-drafts:v1:";
const DERIVED_FIELDS = new Set(["markdown", "content", "content_blocks"]);
const UNSAFE_FIELDS = new Set(["__proto__", "prototype", "constructor"]);
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
const isObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const isId = (value) => typeof value === "string" && value.trim().length > 0;
export const draftKey = (kind, entityId) => `${kind}:${entityId}`;
export const isDerivedDraftField = (field) => DERIVED_FIELDS.has(field);

export function normalizeDraftContext(context) {
  if (
    !context ||
    ![context.userId, context.membershipId, context.organizationId].every(isId)
  )
    return null;
  return {
    userId: context.userId,
    membershipId: context.membershipId,
    organizationId: context.organizationId,
  };
}

export function draftContextKey(context) {
  const normalized = normalizeDraftContext(context);
  return normalized ? JSON.stringify(Object.values(normalized)) : null;
}

export function draftStorageKey(context) {
  const key = draftContextKey(context);
  return key ? DRAFT_STORAGE_PREFIX + encodeURIComponent(key) : null;
}

function same(left, right) {
  if (left === right) return true;
  try {
    return JSON.stringify(left) === JSON.stringify(right);
  } catch {
    return false;
  }
}

// Reject lossy JSON (undefined, NaN, Dates, cycles, etc.) instead of silently
// persisting a different edit. Missing originals have a separate wire encoding.
function cloneJson(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean")
    return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (Array.isArray(value)) return value.map(cloneJson);
  if (
    isObject(value) &&
    [Object.prototype, null].includes(Object.getPrototypeOf(value))
  ) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => {
        if (UNSAFE_FIELDS.has(key)) throw new Error("Unsafe draft field");
        return [key, cloneJson(item)];
      }),
    );
  }
  throw new Error("Draft value is not JSON-safe");
}

function hasChanges(changes) {
  return Object.keys(changes).some((field) => !isDerivedDraftField(field));
}

function toWire(edit) {
  const fields = Object.keys(edit.changes);
  return {
    key: edit.key,
    kind: edit.kind,
    courseId: edit.courseId,
    entityId: edit.entityId,
    label: edit.label,
    changes: cloneJson(edit.changes),
    original: Object.fromEntries(
      fields
        .filter((field) => edit.original[field] !== undefined)
        .map((field) => [field, cloneJson(edit.original[field])]),
    ),
    missingOriginal: fields.filter(
      (field) => edit.original[field] === undefined,
    ),
  };
}

function fromWire(edit) {
  if (
    !isObject(edit) ||
    !["module", "lesson"].includes(edit.kind) ||
    !isId(edit.courseId) ||
    !isId(edit.entityId) ||
    edit.key !== draftKey(edit.kind, edit.entityId) ||
    typeof edit.label !== "string" ||
    !isObject(edit.changes) ||
    !isObject(edit.original) ||
    !Array.isArray(edit.missingOriginal)
  ) {
    throw new Error("Invalid draft snapshot");
  }
  const changes = cloneJson(edit.changes);
  const original = cloneJson(edit.original);
  const fields = Object.keys(changes);
  if (
    !hasChanges(changes) ||
    edit.missingOriginal.some(
      (field) =>
        typeof field !== "string" ||
        !own(changes, field) ||
        own(original, field),
    ) ||
    Object.keys(original).some((field) => !own(changes, field))
  )
    throw new Error("Invalid draft fields");
  for (const field of fields) {
    if (!own(original, field)) {
      if (!edit.missingOriginal.includes(field))
        throw new Error("Missing draft original");
      original[field] = undefined;
    }
    if (same(original[field], changes[field]))
      throw new Error("Draft contains unchanged fields");
  }
  return {
    key: edit.key,
    kind: edit.kind,
    courseId: edit.courseId,
    entityId: edit.entityId,
    label: edit.label,
    original,
    changes,
    error: "",
  };
}

/** Inject storage for SSR/tests. Context is explicitly supplied by the authenticated UI.
 * No tokens, full entities, transient errors or backend responses are persisted.
 * CAS protects async operations in this store instance, not cross-tab transactions.
 */
export function createEditorDraftState(
  set,
  get,
  { getStorage = () => globalThis.localStorage } = {},
) {
  let generation = 0;
  let version = 0;
  const cancelled = new Map();
  const acknowledged = new Map();
  const cancelledCourses = new Map();
  const warning = (operation, error) =>
    set({
      storageWarning: {
        operation,
        message:
          "Не удалось сохранить или восстановить черновики. Правки в памяти доступны, но могут быть потеряны при перезагрузке.",
        detail: error instanceof Error ? error.message : String(error),
      },
    });
  const persist = () => {
    const state = get();
    if (!state.context) return false;
    try {
      const storage = getStorage();
      if (!storage) throw new Error("Storage unavailable");
      const key = draftStorageKey(state.context);
      const edits = Object.values(state.edits).map(toWire);
      if (edits.length)
        storage.setItem(
          key,
          JSON.stringify({
            version: DRAFT_STORAGE_VERSION,
            context: state.context,
            edits,
          }),
        );
      else storage.removeItem(key);
      set({ storageWarning: null });
      return true;
    } catch (error) {
      warning("write", error);
      return false;
    }
  };
  const stamp = (edit) => ({
    ...edit,
    snapshotVersion: ++version,
    contextKey: get().contextKey,
    scopeGeneration: generation,
  });
  const matches = (snapshot) =>
    Boolean(
      snapshot &&
      Number.isSafeInteger(snapshot.snapshotVersion) &&
      snapshot.contextKey === get().contextKey &&
      snapshot.scopeGeneration === generation &&
      get().edits[snapshot.key]?.snapshotVersion === snapshot.snapshotVersion,
    );
  const remove = (key) => {
    cancelled.set(key, version);
    if (!own(get().edits, key)) return false;
    const edits = { ...get().edits };
    delete edits[key];
    set({ edits });
    persist();
    return true;
  };
  return {
    edits: {},
    revision: 0,
    context: null,
    contextKey: null,
    storageWarning: null,
    // Repeating the same context never rehydrates over live edits. Call null on logout
    // or before resolving a new identity; old callbacks then fail their CAS check.
    setContext: (context) => {
      const normalized = normalizeDraftContext(context);
      if (context != null && !normalized)
        throw new Error(
          "Draft context requires userId, membershipId and organizationId",
        );
      const contextKey = draftContextKey(normalized);
      if (contextKey === get().contextKey) return;
      generation += 1;
      cancelled.clear();
      acknowledged.clear();
      cancelledCourses.clear();
      set({
        context: normalized,
        contextKey,
        edits: {},
        storageWarning: null,
        revision: get().revision + 1,
      });
      if (!normalized) return;
      try {
        const storage = getStorage();
        if (!storage) throw new Error("Storage unavailable");
        const raw = storage.getItem(draftStorageKey(normalized));
        if (raw === null) return;
        const data = JSON.parse(raw);
        if (
          data?.version !== DRAFT_STORAGE_VERSION ||
          draftContextKey(data.context) !== contextKey ||
          !Array.isArray(data.edits)
        ) {
          throw new Error("Unsupported or mismatched draft snapshot");
        }
        const edits = {};
        for (const value of data.edits) {
          const edit = fromWire(value);
          if (own(edits, edit.key)) throw new Error("Duplicate draft key");
          edits[edit.key] = stamp(edit);
        }
        set({ edits });
      } catch (error) {
        warning("read", error);
      }
    },
    retryPersistence: persist,
    bumpRevision: () => set({ revision: get().revision + 1 }),
    recordEdit: ({ kind, courseId, entityId, label, entity, changes }) => {
      if (
        !get().context ||
        !["module", "lesson"].includes(kind) ||
        !isId(courseId) ||
        !isId(entityId) ||
        !isObject(changes)
      )
        return false;
      const key = draftKey(kind, entityId);
      const current = get().edits[key];
      if (current && current.courseId !== courseId) return false;
      const original = { ...current?.original };
      const nextChanges = { ...current?.changes };
      try {
        for (const [field, value] of Object.entries(changes)) {
          if (UNSAFE_FIELDS.has(field)) throw new Error("Unsafe draft field");
          const nextValue = cloneJson(value);
          if (!own(original, field))
            original[field] =
              entity?.[field] === undefined
                ? undefined
                : cloneJson(entity[field]);
          if (same(original[field], nextValue)) {
            delete nextChanges[field];
            delete original[field];
          } else nextChanges[field] = nextValue;
        }
      } catch (error) {
        warning("serialize", error);
        return false;
      }
      const edits = { ...get().edits };
      if (hasChanges(nextChanges))
        edits[key] = stamp({
          key,
          kind,
          courseId,
          entityId,
          label: label || current?.label || "",
          original,
          changes: nextChanges,
          error: "",
        });
      else delete edits[key];
      set({ edits });
      persist();
      return true;
    },
    setEditError: (key, error, snapshot) => {
      if (
        !get().edits[key] ||
        (snapshot && (snapshot.key !== key || !matches(snapshot)))
      )
        return false;
      set({
        edits: {
          ...get().edits,
          [key]: { ...get().edits[key], error: String(error || "") },
        },
      });
      return true;
    },
    // Legacy unconditional deletion: explicit discard/entity deletion only, NEVER async save.
    removeEdit: (key, snapshot) =>
      snapshot
        ? snapshot.key === key && matches(snapshot)
          ? remove(key)
          : false
        : remove(key),
    removeSavedSnapshot: (snapshot) =>
      matches(snapshot) ? remove(snapshot.key) : false,
    // Use after ALL requests for this snapshot succeeded. Saves for the same
    // entity must be serialized. A later edit is rebased, never blindly deleted.
    acknowledgeSavedSnapshot: (snapshot) => {
      if (
        !snapshot ||
        !Number.isSafeInteger(snapshot.snapshotVersion) ||
        snapshot.contextKey !== get().contextKey ||
        snapshot.scopeGeneration !== generation ||
        (cancelled.get(snapshot.key) || 0) >= snapshot.snapshotVersion ||
        (cancelledCourses.get(snapshot.courseId) || 0) >=
          snapshot.snapshotVersion ||
        (acknowledged.get(snapshot.key) || 0) >= snapshot.snapshotVersion
      )
        return "stale";
      acknowledged.set(snapshot.key, snapshot.snapshotVersion);
      if (matches(snapshot)) {
        remove(snapshot.key);
        return "removed";
      }
      const current = get().edits[snapshot.key];
      const changes = { ...current?.changes };
      const original = { ...current?.original };
      for (const [field, savedValue] of Object.entries(snapshot.changes)) {
        // An absent field means the user reverted it while the save was in flight.
        const desired = own(changes, field)
          ? changes[field]
          : snapshot.original[field];
        if (same(desired, savedValue)) {
          delete changes[field];
          delete original[field];
        } else {
          changes[field] = desired;
          original[field] = savedValue;
        }
      }
      const edits = { ...get().edits };
      if (hasChanges(changes))
        edits[snapshot.key] = stamp({
          ...(current || snapshot),
          original,
          changes,
          error: current?.error || "",
        });
      else delete edits[snapshot.key];
      set({ edits });
      persist();
      return "rebased";
    },
    isCurrentSnapshot: matches,
    removeEntity: (kind, entityId) => remove(draftKey(kind, entityId)),
    clearCourse: (courseId) => {
      cancelledCourses.set(courseId, version);
      set({
        edits: Object.fromEntries(
          Object.entries(get().edits).filter(
            ([, edit]) => edit.courseId !== courseId,
          ),
        ),
      });
      persist();
    },
    getCourseEdits: (courseId) =>
      Object.values(get().edits).filter((edit) => edit.courseId === courseId),
  };
}
