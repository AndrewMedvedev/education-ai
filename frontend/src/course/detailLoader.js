/**
 * Per-key loading state without React or transport dependencies.
 * run returns the same promise for pending/success entries; errors reject and
 * allow a retry. Even an empty result is successful once apply completes.
 * reset/forget invalidate attempts, not just keys (including A → B → A).
 * Invalidation cannot undo an apply callback that has already started.
 */
export function createDetailLoader() {
  const entries = new Map();

  function run(key, load, apply) {
    const existing = entries.get(key);
    if (existing && existing.status !== "error") return existing.promise;

    const entry = { status: "pending", promise: null };
    const isCurrent = () => entries.get(key) === entry;
    entries.set(key, entry);

    // Defer callbacks so reentrant runs also see the shared promise.
    entry.promise = Promise.resolve()
      .then(() => {
        if (isCurrent()) return load();
      })
      .then(async (value) => {
        if (!isCurrent()) return;
        await apply(value);
        if (!isCurrent()) return;
        entry.status = "success";
        return value;
      })
      .catch((error) => {
        if (isCurrent()) entry.status = "error";
        throw error;
      });

    return entry.promise;
  }

  return {
    run,
    getStatus: (key) => entries.get(key)?.status ?? "idle",
    forget: (key) => entries.delete(key),
    reset: () => entries.clear(),
  };
}
