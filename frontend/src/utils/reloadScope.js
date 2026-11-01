import { create } from "zustand";
import { useSessionStore } from "../stores/sessionStore";
import { getLocalStorage } from "./storage";
import { createScopedStorage, reloadScope } from "./reloadPersistence.js";

// Kept outside persisted stores: quota reporting must not itself write to storage.
export const useReloadStorageErrors = create(() => ({ errors: {} }));
export function reportReloadStorage({
  scope = getReloadScope(),
  name,
  method,
  error,
}) {
  if (!scope) return;
  const key = JSON.stringify([
    scope,
    name,
    method === "getItem" ? "read" : "write",
  ]);
  const errors = useReloadStorageErrors.getState().errors;
  if (Boolean(errors[key]) === Boolean(error)) return;
  const next = { ...errors };
  if (error) next[key] = { scope, name };
  else delete next[key];
  useReloadStorageErrors.setState({ errors: next });
}
export const getReloadScope = () => reloadScope(useSessionStore.getState());
export const getReloadStorage = (scope) =>
  createScopedStorage(getLocalStorage, () => scope, reportReloadStorage);
export const scopedReloadStorage = createScopedStorage(
  getLocalStorage,
  getReloadScope,
  reportReloadStorage,
);

// Reset with writes disabled so an empty old store cannot overwrite the new scope.
export function bindReloadScope(store, reset) {
  let scope = getReloadScope();
  let session = useSessionStore.getState().sessionContext;
  useSessionStore.subscribe((state) => {
    const next = reloadScope(state);
    if (next === scope && session === state.sessionContext) return;
    const previousScope = scope;
    scope = next;
    session = state.sessionContext;
    const storage = store.persist?.getOptions().storage;
    store.persist?.setOptions({
      storage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
    });
    reset(previousScope);
    if (storage) {
      store.persist.setOptions({ storage });
      store.persist.rehydrate();
    }
  });
}
