const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const CONTENT_FIELDS = new Set(["contentBlocks", "content_blocks", "markdown", "content"]);

function equal(left, right) {
  if (Object.is(left, right)) return true;
  if (!left || !right || typeof left !== "object" || typeof right !== "object") return false;
  if (Array.isArray(left) !== Array.isArray(right)) return false;
  const keys = Object.keys(left);
  return keys.length === Object.keys(right).length && keys.every((key) => own(right, key) && equal(left[key], right[key]));
}

function minutes(value) {
  if (typeof value === "number") return value;
  const match = /(\d+)/.exec(String(value || ""));
  return match ? Number(match[1]) : null;
}

function serverValue(server, field) {
  if (field === "summary") return server.description ?? server.summary;
  if (field === "learning_objectives") return server.learning_objectives ?? server.learningObjectives;
  if (field === "learningObjectives") return server.learningObjectives ?? server.learning_objectives;
  if (field === "content_blocks") return server.contentBlocks ?? server.content_blocks;
  if (field === "contentBlocks") return server.contentBlocks ?? server.content_blocks;
  if (["duration", "estimatedTimeMinutes", "estimated_time_minutes"].includes(field)) {
    return server.estimated_time_minutes ?? server.estimatedTimeMinutes ?? minutes(server.duration);
  }
  return server[field];
}

function comparable(field, value) {
  return ["duration", "estimatedTimeMinutes", "estimated_time_minutes"].includes(field) ? minutes(value) : value;
}

// Follow API alias precedence; derived markdown/content are not separate writes.
function changedFields(edit) {
  return Object.keys(edit.changes).filter((field) => {
    if (field === "markdown" || field === "content") return false;
    if (field === "content_blocks" && own(edit.changes, "contentBlocks")) return false;
    if (field === "description" && edit.kind === "lesson" && own(edit.changes, "summary")) return false;
    if (field === "learningObjectives" && own(edit.changes, "learning_objectives")) return false;
    if (["estimatedTimeMinutes", "estimated_time_minutes"].includes(field) && own(edit.changes, "duration")) return false;
    if (field === "estimatedTimeMinutes" && own(edit.changes, "estimated_time_minutes")) return false;
    return true;
  });
}

export function draftConflicts(edit, server) {
  return changedFields(edit).filter((field) => {
    const current = serverValue(server, field);
    return !equal(current, comparable(field, edit.original[field])) &&
      !equal(current, comparable(field, edit.changes[field]));
  });
}

// Basic-info mappers synthesize empty children/content. Never merge these over
// separately loaded details. Content-only responses synthesize metadata too.
export function editorServerFields(kind, entity, contentOnly = false) {
  return Object.fromEntries(Object.entries(entity).filter(([field]) => {
    if (field === "id") return true;
    if (kind === "module") return !["lessons", "practice"].includes(field);
    return contentOnly ? CONTENT_FIELDS.has(field) : !CONTENT_FIELDS.has(field);
  }));
}

export function serializeEditorSave(queue, task) {
  const pending = queue.current.catch(() => {}).then(task);
  queue.current = pending.catch(() => {});
  return pending;
}

/** All IO is injected so conflict, partial failure and session races are testable.
 * Each batch is serialized by the caller. Checks bracket every awaited request.
 * Preflight is optimistic only: atomic protection against GET/PUT races requires
 * backend ETag/If-Match or an entity revision, which this API does not expose.
 */
export async function saveEditorDrafts(edits, {
  drafts, isContextCurrent, getModule, getLesson, getTheory,
  updateModule, updateLesson, mergeServer, forgetTheory = () => {}, errorMessage = (error) => error.message,
}) {
  let success = true;
  for (const edit of edits) {
    if (!isContextCurrent()) return false;
    // A queued save may refer to an already acknowledged or replaced snapshot.
    if (!drafts.isCurrentSnapshot(edit)) { success = false; continue; }
    try {
      const fresh = edit.kind === "module" ? await getModule(edit.entityId) : await getLesson(edit.entityId);
      if (!isContextCurrent()) return false;
      mergeServer(edit, editorServerFields(edit.kind, fresh));
      const blocks = edit.changes.contentBlocks ?? edit.changes.content_blocks;
      if (edit.kind === "lesson" && blocks !== undefined) {
        const theory = await getTheory(edit.entityId);
        if (!isContextCurrent()) return false;
        Object.assign(fresh, { contentBlocks: theory, content_blocks: theory });
        mergeServer(edit, { id: edit.entityId, contentBlocks: theory, content_blocks: theory });
      }
      const conflicts = draftConflicts(edit, fresh);
      if (conflicts.length) {
        throw new Error(`Конфликт изменений (${conflicts.join(", ")}). Серверная версия изменилась. Черновик сохранён; отмените или согласуйте правки.`);
      }
      // No write if edits were changed/discarded while preflight was loading.
      if (!drafts.isCurrentSnapshot(edit)) { success = false; continue; }
      const pendingFields = changedFields(edit).filter((field) =>
        !equal(serverValue(fresh, field), comparable(field, edit.changes[field])));
      if (edit.kind === "module") {
        if (pendingFields.length) {
          const saved = await updateModule(edit.courseId, edit.entityId, edit.changes);
          if (!isContextCurrent()) return false;
          if (!saved) throw new Error("Сервер не подтвердил сохранение модуля.");
          mergeServer(edit, editorServerFields("module", saved));
        }
      } else {
        const meta = Object.fromEntries(Object.entries(edit.changes).filter(([field]) => !CONTENT_FIELDS.has(field)));
        if (pendingFields.some((field) => !CONTENT_FIELDS.has(field))) {
          const saved = await updateLesson(edit.courseId, edit.entityId, meta);
          if (!isContextCurrent()) return false;
          if (!saved) throw new Error("Сервер не подтвердил сохранение урока.");
          mergeServer(edit, editorServerFields("lesson", saved));
        }
        if (pendingFields.some((field) => field === "contentBlocks" || field === "content_blocks")) {
          if (!isContextCurrent()) return false;
          const saved = await updateLesson(edit.courseId, edit.entityId, { contentBlocks: blocks });
          if (!isContextCurrent()) return false;
          if (!saved) throw new Error("Сервер не подтвердил сохранение содержимого урока.");
          mergeServer(edit, editorServerFields("lesson", saved, true));
          forgetTheory(edit.entityId);
        }
      }
      if (!isContextCurrent()) return false;
      if (drafts.acknowledgeSavedSnapshot(edit) === "stale") success = false;
    } catch (error) {
      if (!isContextCurrent()) return false;
      success = false;
      drafts.setEditError(edit.key, errorMessage(error), edit);
    }
  }
  return success;
}
