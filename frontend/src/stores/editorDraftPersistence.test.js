import test from "node:test";
import assert from "node:assert/strict";
import {
  createEditorDraftState,
  draftStorageKey,
  DRAFT_STORAGE_VERSION,
} from "./editorDraftPersistence.js";

const context = {
  userId: "user-1",
  membershipId: "member-1",
  organizationId: "org-1",
};
const input = {
  kind: "lesson",
  courseId: "course-1",
  entityId: "lesson-1",
  label: "Lesson",
  entity: { title: "Before", description: "Original" },
  changes: { title: "After" },
};
test("acknowledgement removes an exact snapshot and cannot be replayed", () => {
  const s = active();
  s.get().recordEdit(input);
  const saved = edit(s);
  assert.equal(s.get().acknowledgeSavedSnapshot(saved), "removed");
  assert.equal(s.get().acknowledgeSavedSnapshot(saved), "stale");
  assert.equal(s.storage.data.size, 0);
});

test("acknowledgement rebases concurrent fields and persists only remaining deltas", () => {
  const s = active();
  s.get().recordEdit({
    ...input,
    changes: { title: "Saved", description: "Saved description" },
  });
  const saved = edit(s);
  s.get().recordEdit({ ...input, changes: { title: "Newer" } });
  assert.equal(s.get().acknowledgeSavedSnapshot(saved), "rebased");
  assert.deepEqual(edit(s).changes, { title: "Newer" });
  assert.deepEqual(edit(s).original, { title: "Saved" });
  assert.deepEqual(edit(active(s.storage)).changes, { title: "Newer" });
  assert.equal(s.get().acknowledgeSavedSnapshot(saved), "stale");
  s.get().recordEdit({
    ...input,
    entity: { title: "Saved" },
    changes: { title: "Saved" },
  });
  assert.deepEqual(s.get().edits, {});
});

test("a revert while saving becomes a pending delta against the saved value", () => {
  const s = active();
  s.get().recordEdit(input);
  const saved = edit(s);
  s.get().recordEdit({ ...input, changes: { title: "Before" } });
  assert.deepEqual(s.get().edits, {});
  assert.equal(s.get().acknowledgeSavedSnapshot(saved), "rebased");
  assert.deepEqual(edit(s).original, { title: "After" });
  assert.deepEqual(edit(s).changes, { title: "Before" });
  assert.deepEqual(edit(active(s.storage)).changes, { title: "Before" });
});

for (const cancel of [
  (s, saved) => s.get().removeEdit(saved.key),
  (s) => s.get().clearCourse(input.courseId),
  (s) => {
    s.get().setContext(null);
    s.get().setContext(context);
  },
]) {
  test("save acknowledgement never resurrects an explicitly discarded scope/entity", () => {
    const s = active();
    s.get().recordEdit(input);
    const saved = edit(s);
    s.get().recordEdit({ ...input, changes: { title: "Before" } });
    cancel(s, saved);
    const before = s.get().edits;
    assert.equal(s.get().acknowledgeSavedSnapshot(saved), "stale");
    assert.equal(s.get().edits, before);
  });
}

function memoryStorage() {
  const data = new Map();
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
  };
}
function store(storage = memoryStorage()) {
  let state;
  const set = (patch) => {
    state = {
      ...state,
      ...(typeof patch === "function" ? patch(state) : patch),
    };
  };
  state = createEditorDraftState(set, () => state, {
    getStorage: () => storage,
  });
  return { get: () => state, storage };
}
function active(storage) {
  const result = store(storage);
  result.get().setContext(context);
  return result;
}
const edit = (s) => s.get().getCourseEdits("course-1")[0];

test("versioned reload persists deltas only, never full entities, errors or session data", () => {
  const s = active();
  s.get().recordEdit({
    ...input,
    entity: { ...input.entity, secret: "not a draft", accessToken: "secret" },
  });
  const snapshot = edit(s);
  s.get().setEditError(snapshot.key, "server failure");
  const wire = JSON.parse(s.storage.getItem(draftStorageKey(context)));
  assert.equal(wire.version, DRAFT_STORAGE_VERSION);
  assert.deepEqual(wire.edits[0].original, { title: "Before" });
  assert.deepEqual(wire.edits[0].changes, { title: "After" });
  assert.equal(wire.edits[0].error, undefined);
  assert.equal(wire.edits[0].entity, undefined);
  assert.equal(JSON.stringify(wire).includes("secret"), false);
  const restored = active(s.storage);
  assert.equal(edit(restored).changes.title, "After");
  assert.equal(edit(restored).error, "");
});

test("only a complete explicit context can record; context keys are collision safe", () => {
  const s = store();
  assert.equal(s.get().recordEdit(input), false);
  assert.deepEqual(s.get().edits, {});
  assert.throws(() => s.get().setContext({ userId: "x" }), /requires/);
  assert.notEqual(
    draftStorageKey({ userId: "a:b", membershipId: "c", organizationId: "d" }),
    draftStorageKey({ userId: "a", membershipId: "b:c", organizationId: "d" }),
  );
});

for (const field of ["userId", "membershipId", "organizationId"]) {
  test(`isolation on ${field} change and logout; returning restores only that scope`, () => {
    const s = active();
    s.get().recordEdit(input);
    const old = edit(s);
    s.get().setContext({ ...context, [field]: "other" });
    assert.deepEqual(s.get().edits, {});
    s.get().recordEdit({ ...input, changes: { title: "Other scope" } });
    assert.equal(s.get().removeSavedSnapshot(old), false);
    s.get().setContext(null);
    assert.deepEqual(s.get().edits, {});
    s.get().setContext(context);
    assert.equal(edit(s).changes.title, "After");
    assert.equal(s.get().removeSavedSnapshot(old), false);
  });
}

test("same context is idempotent and never reloads over live edits", () => {
  const s = active();
  s.get().recordEdit(input);
  const before = edit(s);
  s.storage.getItem = () => {
    throw new Error("should not read again");
  };
  s.get().setContext({ ...context });
  assert.equal(edit(s), before);
  assert.equal(s.get().storageWarning, null);
});

test("CAS keeps concurrent edits, including ABA; exact snapshot removes durable entry", () => {
  const s = active();
  s.get().recordEdit(input);
  const saving = edit(s);
  s.get().recordEdit({ ...input, changes: { title: "Newer" } });
  assert.equal(s.get().removeSavedSnapshot(saving), false);
  assert.equal(s.get().removeEdit(saving.key, saving), false);
  assert.equal(
    s.get().setEditError(saving.key, "stale failure", saving),
    false,
  );
  s.get().recordEdit(input);
  assert.equal(s.get().removeSavedSnapshot(saving), false);
  assert.equal(
    s.get().removeSavedSnapshot({ ...edit(s), contextKey: "other" }),
    false,
  );
  assert.equal(s.get().removeSavedSnapshot(edit(s)), true);
  assert.equal(s.storage.getItem(draftStorageKey(context)), null);
  assert.deepEqual(active(s.storage).get().edits, {});
});

test("CAS rejects snapshots after discard/recreate and course clear", () => {
  const s = active();
  assert.equal(
    s.get().isCurrentSnapshot({
      contextKey: s.get().contextKey,
      scopeGeneration: 1,
      key: "absent",
    }),
    false,
  );
  s.get().recordEdit(input);
  const old = edit(s);
  s.get().removeEdit(old.key);
  s.get().recordEdit(input);
  assert.equal(s.get().removeSavedSnapshot(old), false);
  const newer = edit(s);
  s.get().clearCourse(input.courseId);
  s.get().recordEdit(input);
  assert.equal(s.get().removeSavedSnapshot(newer), false);
  assert.equal(s.get().isCurrentSnapshot(edit(s)), true);
});

test("reverting fields prunes originals and removes empty/derived-only entries", () => {
  const s = active();
  s.get().recordEdit({
    ...input,
    changes: { title: "After", description: "Changed" },
  });
  s.get().recordEdit({ ...input, changes: { title: "Before" } });
  assert.deepEqual(edit(s).original, { description: "Original" });
  assert.deepEqual(edit(s).changes, { description: "Changed" });
  s.get().recordEdit({
    ...input,
    changes: { description: "Original", markdown: "derived" },
  });
  assert.deepEqual(s.get().edits, {});
  assert.equal(s.storage.data.size, 0);
});

test("missing originals survive reload as undefined, distinct from null", () => {
  const s = active();
  s.get().recordEdit({ ...input, changes: { newField: null } });
  const restored = active(s.storage);
  assert.equal(Object.hasOwn(edit(restored).original, "newField"), true);
  assert.equal(edit(restored).original.newField, undefined);
  assert.equal(edit(restored).changes.newField, null);
});

test("nested draft values are detached from editor input", () => {
  const s = active();
  const entity = { contentBlocks: [{ text: "old" }] };
  const changes = { contentBlocks: [{ text: "new" }] };
  s.get().recordEdit({ ...input, entity, changes });
  entity.contentBlocks[0].text = "mutated";
  changes.contentBlocks[0].text = "mutated";
  assert.equal(edit(s).original.contentBlocks[0].text, "old");
  assert.equal(edit(s).changes.contentBlocks[0].text, "new");
});

for (const operation of ["getItem", "setItem", "removeItem"]) {
  test(`storage ${operation} failure is nonfatal and observable; retry clears warning`, () => {
    const storage = memoryStorage();
    const original = storage[operation];
    storage[operation] = () => {
      throw new Error("denied/quota");
    };
    const s = active(storage);
    if (operation === "getItem") {
      assert.equal(s.get().storageWarning.operation, "read");
    } else {
      assert.equal(s.get().recordEdit(input), true);
      if (operation === "removeItem") s.get().removeEdit(edit(s).key);
      assert.equal(s.get().storageWarning.operation, "write");
    }
    storage[operation] = original;
    assert.equal(s.get().retryPersistence(), true);
    assert.equal(s.get().storageWarning, null);
  });
}

test("unavailable browser storage does not break editing", () => {
  const s = active(null);
  assert.equal(s.get().storageWarning.operation, "read");
  assert.equal(s.get().recordEdit(input), true);
  assert.equal(edit(s).changes.title, "After");
  assert.equal(s.get().storageWarning.operation, "write");
});

for (const mutate of [
  () => "not json",
  (data) => ({ ...data, version: 99 }),
  (data) => ({ ...data, context: { ...context, userId: "other" } }),
  (data) => ({
    ...data,
    edits: [...data.edits, { ...data.edits[0], kind: "invalid" }],
  }),
  (data) => ({ ...data, edits: [...data.edits, data.edits[0]] }),
  (data) => ({ ...data, edits: [{ ...data.edits[0], original: {} }] }),
  (data) => ({
    ...data,
    edits: [
      {
        ...data.edits[0],
        changes: JSON.parse('{"__proto__":{"polluted":true}}'),
      },
    ],
  }),
]) {
  test("malformed/unsupported storage is rejected atomically and left intact", () => {
    const s = active();
    s.get().recordEdit(input);
    const key = draftStorageKey(context);
    const changed = mutate(JSON.parse(s.storage.getItem(key)));
    const raw = typeof changed === "string" ? changed : JSON.stringify(changed);
    s.storage.setItem(key, raw);
    const restored = active(s.storage);
    assert.deepEqual(restored.get().edits, {});
    assert.equal(restored.get().storageWarning.operation, "read");
    assert.equal(s.storage.getItem(key), raw);
    assert.equal({}.polluted, undefined);
  });
}

test("invalid non-JSON edits do not corrupt existing drafts", () => {
  const s = active();
  s.get().recordEdit(input);
  const snapshot = edit(s);
  for (const value of [undefined, NaN, Infinity, new Date(), 1n]) {
    assert.equal(
      s.get().recordEdit({ ...input, changes: { title: value } }),
      false,
    );
    assert.equal(edit(s), snapshot);
    assert.equal(s.get().storageWarning.operation, "serialize");
  }
});

test("explicit discard, entity deletion and clearCourse persist removals", () => {
  const s = active();
  s.get().recordEdit(input);
  s.get().recordEdit({ ...input, kind: "module", entityId: "module-1" });
  s.get().recordEdit({ ...input, courseId: "course-2", entityId: "lesson-2" });
  s.get().removeEntity("module", "module-1");
  s.get().clearCourse("course-1");
  const restored = active(s.storage);
  assert.deepEqual(Object.keys(restored.get().edits), ["lesson:lesson-2"]);
  restored.get().removeEdit("lesson:lesson-2");
  assert.equal(s.storage.data.size, 0);
});
