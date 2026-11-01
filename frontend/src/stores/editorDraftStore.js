import { create } from "zustand";
import { createEditorDraftState } from "./editorDraftPersistence.js";

export { draftKey, isDerivedDraftField } from "./editorDraftPersistence.js";

/**
 * Unsaved module/lesson deltas only. Before recording or restoring drafts the UI
 * must setContext({ userId, membershipId, organizationId }) from a confirmed
 * session, and setContext(null) on logout/identity transition.
 *
 * After ALL requests succeed, call acknowledgeSavedSnapshot(edit): it CAS-removes
 * the unchanged snapshot or rebases concurrent edits onto the saved values.
 * Serialize saves per entity. removeSavedSnapshot(edit) / removeEdit(key, edit)
 * offer strict CAS deletion only (false = newer edit/context; no rebasing).
 * removeEdit(key) is for explicit discard only, never async save.
 * Persisted changes must be overlaid by App after each backend data merge;
 * this store deliberately does not own or mutate App's course state.
 */
export const useEditorDraftStore = create(createEditorDraftState);
