import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { applyEntityFields, mergeLesson, mergeModule } from "./courseState.js";
import { createEditorDraftState } from "../stores/editorDraftPersistence.js";
import { draftConflicts, editorServerFields, saveEditorDrafts, serializeEditorSave } from "./editorDraftSave.js";

const context = { userId: "user", membershipId: "member", organizationId: "org" };
const courseId = "11111111-1111-4111-8111-111111111111";
const moduleId = "22222222-2222-4222-8222-222222222222";
const lessonId = "33333333-3333-4333-8333-333333333333";
const theory = [{ content_type: "text", md_content: "Before" }];
const nextTheory = [{ content_type: "text", md_content: "After" }];
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function fixture(kind = "lesson", changes = { title: "After" }) {
  let state;
  state = createEditorDraftState((patch) => { state = { ...state, ...patch }; }, () => state, {
    getStorage: () => ({ getItem: () => null, setItem() {}, removeItem() {} }),
  });
  state.setContext(context);
  const lesson = { id: lessonId, title: "Before", description: "Description", summary: "Description", contentBlocks: theory, content_blocks: theory };
  const block = { id: moduleId, title: "Before", description: "Description", lessons: [lesson], practice: [] };
  let courses = [{ id: courseId, blocks: [block] }];
  const entity = kind === "module" ? block : lesson;
  state.recordEdit({ kind, courseId, entityId: entity.id, entity, changes });
  const snapshot = Object.values(state.edits)[0];
  const calls = [];
  const deps = {
    drafts: state,
    isContextCurrent: () => true,
    getModule: async () => ({ ...block }),
    getLesson: async () => ({ ...lesson }),
    getTheory: async () => theory,
    updateModule: async (_course, id, fields) => { calls.push(fields); return { ...block, id, ...fields }; },
    updateLesson: async (_course, id, fields) => { calls.push(fields); return { ...lesson, id, ...fields }; },
    mergeServer: (edit, fields) => { courses = courses.map((course) => edit.kind === "module" ? mergeModule(course, fields) : mergeLesson(course, fields)); },
    forgetTheory: () => calls.push("forgetTheory"),
  };
  return { get: () => state, snapshot, deps, calls, courses: () => courses,
    record: (fields) => state.recordEdit({ kind, courseId, entityId: entity.id, entity, changes: fields }),
    overlay: () => Object.values(state.edits).reduce((all, edit) => all.map((course) => applyEntityFields(course, edit.kind, edit.entityId, edit.changes)), courses),
  };
}

for (const kind of ["module", "lesson"]) {
  test(`${kind}: preflight conflict performs no PUT, retains draft/error and refreshes discard baseline`, async () => {
    const f = fixture(kind);
    const get = kind === "module" ? "getModule" : "getLesson";
    const originalGet = f.deps[get];
    f.deps[get] = async () => ({ ...await originalGet(), title: "Remote edit" });
    assert.equal(await saveEditorDrafts([f.snapshot], f.deps), false);
    assert.equal(f.calls.length, 0);
    const pending = f.get().edits[f.snapshot.key];
    assert.match(pending.error, /Конфликт.*title/);
    assert.equal(pending.changes.title, "After");
    const entity = (courses) => kind === "module" ? courses[0].blocks[0] : courses[0].blocks[0].lessons[0];
    assert.equal(entity(f.overlay()).title, "After");
    f.get().removeEdit(pending.key, pending);
    assert.equal(entity(f.overlay()).title, "Remote edit");
  });
}

test("server already equal to changes needs no write and acknowledges snapshot", async () => {
  const f = fixture();
  const get = f.deps.getLesson;
  f.deps.getLesson = async () => ({ ...await get(), title: "After" });
  assert.equal(await saveEditorDrafts([f.snapshot], f.deps), true);
  assert.deepEqual(f.calls, []);
  assert.deepEqual(f.get().edits, {});
});

test("a changed unrelated field does not cause a conflict", () => {
  assert.deepEqual(draftConflicts({ kind: "module", original: { title: "Before" }, changes: { title: "After" } }, { title: "Before", description: "Remote" }), []);
});

test("comparison is structural, respects alias precedence, duration and derived fields", () => {
  const edit = { kind: "lesson", original: { summary: "Before", duration: "20 минут", learningObjectives: [{ a: 1, b: 2 }], contentBlocks: theory },
    changes: { summary: "After", duration: "30 минут", learningObjectives: [], contentBlocks: nextTheory, markdown: "derived", content_blocks: [] } };
  assert.deepEqual(draftConflicts(edit, { description: "Before", duration: "20 мин.", learning_objectives: [{ b: 2, a: 1 }], contentBlocks: theory }), []);
  assert.deepEqual(draftConflicts(edit, { description: "Other", duration: "40 мин.", learningObjectives: [], contentBlocks: theory }), ["summary", "duration"]);
});

test("theory GET is included in preflight; a content conflict prevents metadata PUT too", async () => {
  const f = fixture("lesson", { title: "After", contentBlocks: nextTheory });
  f.deps.getTheory = async () => [{ content_type: "text", md_content: "Remote" }];
  assert.equal(await saveEditorDrafts([f.snapshot], f.deps), false);
  assert.deepEqual(f.calls, []);
  assert.match(f.get().edits[f.snapshot.key].error, /contentBlocks/);
  assert.equal(f.courses()[0].blocks[0].lessons[0].contentBlocks[0].md_content, "Remote");
});

for (const get of ["getLesson", "getTheory"]) {
  test(`404 from ${get} retains the draft and never writes`, async () => {
    const f = fixture("lesson", { title: "After", contentBlocks: nextTheory });
    f.deps[get] = async () => { throw Object.assign(new Error("Not found"), { status: 404 }); };
    assert.equal(await saveEditorDrafts([f.snapshot], f.deps), false);
    assert.deepEqual(f.calls, []);
    assert.match(f.get().edits[f.snapshot.key].error, /Not found/);
  });
}

test("successful metadata + content save acknowledges only after both; partial errors retain draft", async () => {
  const f = fixture("lesson", { title: "After", contentBlocks: nextTheory });
  const update = f.deps.updateLesson;
  f.deps.updateLesson = async (...args) => {
    if (args[2].contentBlocks) throw new Error("content write failed");
    return update(...args);
  };
  assert.equal(await saveEditorDrafts([f.snapshot], f.deps), false);
  assert.match(f.get().edits[f.snapshot.key].error, /content write failed/);
  assert.equal(f.courses()[0].blocks[0].lessons[0].title, "After");
  assert.deepEqual(f.courses()[0].blocks[0].lessons[0].contentBlocks, theory);
  // Retrying after a partially successful write is not a false conflict.
  f.deps.getLesson = async () => ({ ...f.courses()[0].blocks[0].lessons[0] });
  f.deps.updateLesson = update;
  assert.equal(await saveEditorDrafts([f.get().edits[f.snapshot.key]], f.deps), true);
  assert.deepEqual(f.get().edits, {});
  assert.deepEqual(f.courses()[0].blocks[0].lessons[0].contentBlocks, nextTheory);
});

test("concurrent edit during PUT survives acknowledgement with the saved baseline", async () => {
  const f = fixture();
  const gate = deferred();
  const started = deferred();
  const update = f.deps.updateLesson;
  f.deps.updateLesson = async (...args) => { started.resolve(); await gate.promise; return update(...args); };
  const saving = saveEditorDrafts([f.snapshot], f.deps);
  await started.promise;
  f.record({ title: "Newer" });
  gate.resolve();
  assert.equal(await saving, true);
  const pending = f.get().edits[f.snapshot.key];
  assert.deepEqual(pending.original, { title: "After" });
  assert.deepEqual(pending.changes, { title: "Newer" });
  assert.equal(f.courses()[0].blocks[0].lessons[0].title, "After");
  assert.equal(f.overlay()[0].blocks[0].lessons[0].title, "Newer");
});

test("edit/discard during GET invalidates preflight before any write", async () => {
  for (const change of [(f) => f.record({ title: "Newer" }), (f) => f.get().removeEdit(f.snapshot.key)]) {
    const f = fixture();
    const gate = deferred();
    const get = f.deps.getLesson;
    f.deps.getLesson = async () => { await gate.promise; return get(); };
    const saving = saveEditorDrafts([f.snapshot], f.deps);
    change(f);
    gate.resolve();
    assert.equal(await saving, false);
    assert.deepEqual(f.calls, []);
  }
});

for (const request of ["getLesson", "getTheory", "updateLesson"]) {
  for (const failed of [false, true]) {
    test(`session switch during ${request} (${failed ? "reject" : "resolve"}) has no late effects or further writes`, async () => {
      const f = fixture("lesson", { title: "After", contentBlocks: nextTheory });
      let current = true;
      f.deps.isContextCurrent = () => current;
      const gate = deferred();
      const started = deferred();
      const original = f.deps[request];
      f.deps[request] = async (...args) => {
        const response = await original(...args);
        started.resolve();
        await gate.promise;
        if (failed) throw new Error("late failure");
        return response;
      };
      const saving = saveEditorDrafts([f.snapshot], f.deps);
      await started.promise;
      const courses = f.courses();
      const writes = f.calls.length;
      current = false;
      gate.resolve();
      assert.equal(await saving, false);
      assert.equal(f.courses(), courses);
      assert.equal(f.calls.length, writes);
      assert.equal(f.get().edits[f.snapshot.key].error, "");
    });
  }
}

test("serialization waits for preceding save and survives failures", async () => {
  const queue = { current: Promise.resolve() };
  const gate = deferred();
  const events = [];
  const first = serializeEditorSave(queue, async () => { events.push("first"); await gate.promise; throw new Error("failed"); });
  const second = serializeEditorSave(queue, async () => { events.push("second"); return true; });
  const rejection = assert.rejects(first, /failed/);
  await Promise.resolve(); await Promise.resolve();
  assert.deepEqual(events, ["first"]);
  gate.resolve();
  await rejection;
  assert.equal(await second, true);
  assert.deepEqual(events, ["first", "second"]);
});

test("duplicated queued snapshot does not cause a duplicate PUT", async () => {
  const f = fixture();
  const queue = { current: Promise.resolve() };
  const first = serializeEditorSave(queue, () => saveEditorDrafts([f.snapshot], f.deps));
  const second = serializeEditorSave(queue, () => saveEditorDrafts([f.snapshot], f.deps));
  assert.equal(await first, true);
  assert.equal(await second, false);
  assert.equal(f.calls.length, 1);
});

test("server field projection never wipes loaded children or metadata with mapper defaults", () => {
  assert.deepEqual(editorServerFields("module", { id: moduleId, title: "Remote", lessons: [], practice: [] }), { id: moduleId, title: "Remote" });
  assert.deepEqual(editorServerFields("lesson", { id: lessonId, title: "Remote", contentBlocks: [], markdown: "" }), { id: lessonId, title: "Remote" });
  assert.deepEqual(editorServerFields("lesson", { id: lessonId, title: "Synthetic", contentBlocks: nextTheory }, true), { id: lessonId, contentBlocks: nextTheory });
});

// Execute the four non-JSX callbacks directly: no React, bundler or DOM needed.
// This deliberately tests App's actual UUID branch, not a duplicate implementation.
const app = readFileSync(new URL("../App.jsx", import.meta.url), "utf8");
function appCallback(name, next, deps) {
  const source = app.slice(app.indexOf(`  const ${name} =`), app.indexOf(`  const ${next} =`));
  return Function(...Object.keys(deps), `${source}\nreturn ${name};`)(...Object.values(deps));
}

for (const [name, next, kind, id] of [
  ["updateCourseBlock", "insertCourseBlock", "module", moduleId],
  ["updateLesson", "savePendingEdits", "lesson", lessonId],
]) {
  test(`App ${name}: UUID edits never write serverCourses, discard reveals the fresh server baseline`, () => {
    const f = fixture(kind);
    f.get().removeEdit(f.snapshot.key);
    const courses = f.courses();
    let writes = 0;
    const deps = {
      canUpdateCourse: true, sessionContext: 1,
      useSessionStore: { getState: () => ({ sessionContext: 1 }) },
      useEditorDraftStore: { getState: f.get },
      getReloadScope: () => f.get().contextKey,
      isUuid: (value) => /^[0-9a-f-]{36}$/.test(value),
      selectedCourse: courses[0], serverCourses: courses,
      setEditableCourses: () => { writes += 1; },
      applyEntityFields, forgetLessonTheory: () => {},
    };
    const update = appCallback(name, next, deps);
    update(id, { title: "Local edit" });
    assert.equal(writes, 0);
    const pending = Object.values(f.get().edits)[0];
    assert.equal(pending.original.title, "Before");
    const entity = kind === "module" ? courses[0].blocks[0] : courses[0].blocks[0].lessons[0];
    entity.title = "Fresh server title";
    const discard = appCallback("discardPendingEdits", "updatePractice", deps);
    discard([pending]);
    assert.equal(writes, 0);
    assert.deepEqual(f.get().edits, {});
    assert.equal(entity.title, "Fresh server title");
  });
}
