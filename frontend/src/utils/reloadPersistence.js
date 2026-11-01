// Global legacy records have no provable owner and must never be adopted.
export function reloadScope(state) {
  const identity = state.identity;
  const ids = [
    identity?.id || identity?.user_id || identity?.userId,
    state.membershipId,
    state.organizationId,
  ];
  return state.accessToken &&
    ids.every((id) => typeof id === "string" && id.trim())
    ? JSON.stringify(ids)
    : null;
}

export function createScopedStorage(getStorage, getScope, report = () => {}) {
  return Object.fromEntries(
    ["getItem", "setItem", "removeItem"].map((method) => [
      method,
      (name, value) => {
        const scope = getScope();
        if (!scope) return method === "getItem" ? null : false;
        try {
          const storage = getStorage();
          if (!storage) throw new Error("Storage unavailable");
          const result = storage[method](
            `reload-v2:${encodeURIComponent(scope)}:${name}`,
            value,
          );
          report({ scope, name, method, error: null });
          return method === "getItem" ? result : true;
        } catch (error) {
          report({ scope, name, method, error });
          return method === "getItem" ? null : false;
        }
      },
    ]),
  );
}

// Only synchronous local draft writes belong here, never network saves.
export function createDraftDebounce(write, delay = 450, clock = globalThis) {
  let timer = null;
  const cancel = () => {
    if (timer !== null) clock.clearTimeout(timer);
    timer = null;
  };
  const flush = () => {
    cancel();
    write();
  };
  return {
    cancel,
    flush,
    schedule() {
      cancel();
      timer = clock.setTimeout(flush, delay);
    },
  };
}
