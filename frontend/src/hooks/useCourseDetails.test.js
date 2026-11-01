import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";

const C = "11111111-1111-4111-8111-111111111111";
const M = "22222222-2222-4222-8222-222222222222";
const N = "33333333-3333-4333-8333-333333333333";
const L = "44444444-4444-4444-8444-444444444444";
const course = (blocks = [{ id: M }]) => ({ id: C, blocks });
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

// Deterministic render/commit separation, with stable state setters like React.
// Only React and I/O boundaries are stubbed; loader and merge functions are real.
function lifecycle() {
  let slots = [],
    index = 0,
    effects = [],
    dirty = false,
    renderHook,
    value;
  let mounted = true;
  const same = (a, b) =>
    a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
  const react = {
    useState(initial) {
      const i = index++;
      if (!slots[i]) {
        const slot = {
          value: typeof initial === "function" ? initial() : initial,
        };
        slot.set = (next) => {
          const result = typeof next === "function" ? next(slot.value) : next;
          if (!Object.is(result, slot.value)) {
            slot.value = result;
            dirty = true;
          }
        };
        slots[i] = slot;
      }
      return [slots[i].value, slots[i].set];
    },
    useRef(initial) {
      return (slots[index++] ||= { current: initial });
    },
    useEffect(effect, deps) {
      const i = index++;
      if (!slots[i] || !same(slots[i].deps, deps)) {
        const previous = slots[i];
        const slot = { deps };
        slots[i] = slot;
        effects.push(() => {
          previous?.cleanup?.();
          slot.cleanup = effect();
        });
      }
    },
  };
  return {
    react,
    render(fn = renderHook, commit = true) {
      renderHook = fn;
      index = 0;
      dirty = false;
      value = fn();
      if (commit) this.commit();
      return value;
    },
    commit() {
      const pending = effects;
      effects = [];
      pending.forEach((effect) => effect());
    },
    async flush() {
      for (let i = 0; i < 120; i++) {
        await Promise.resolve();
        if (mounted && dirty) this.render();
      }
      assert.equal(
        dirty && mounted,
        false,
        "hook did not settle (render/request loop)",
      );
      return value;
    },
    replayEffects() {
      slots.forEach((slot) => {
        if (slot?.cleanup) slot.cleanup();
      });
      // React StrictMode replays effect setup without discarding refs/state.
      slots.forEach((slot) => {
        if (slot?.deps) slot.deps = undefined;
      });
      this.render();
    },
    unmount() {
      mounted = false;
      slots.forEach((slot) => slot?.cleanup?.());
    },
    get value() {
      return value;
    },
  };
}

const bundle = await build({
  entryPoints: [new URL("./useCourseDetails.js", import.meta.url).pathname],
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  plugins: [
    {
      name: "boundaries",
      setup(builder) {
        builder.onResolve(
          { filter: /^react$|\/utils\/api$|\/stores\/sessionStore$/ },
          ({ path }) => ({ path, external: true }),
        );
      },
    },
  ],
});

function setup(initial = [course()]) {
  const runner = lifecycle();
  let context = 1;
  const calls = { course: [], module: [], lesson: [] };
  const service = {
    getCourse: async () => course(),
    getModuleBasicInfo: async (id) => ({ id, lessons: [], practice: [] }),
    getLessonBasicInfo: async (id) => ({ id, title: "detail" }),
  };
  const api = { isUuid: (id) => /^[0-9a-f-]{36}$/.test(id) };
  for (const [name, kind] of [
    ["getCourse", "course"],
    ["getModuleBasicInfo", "module"],
    ["getLessonBasicInfo", "lesson"],
  ]) {
    api[name] = (id) => {
      calls[kind].push(id);
      return service[name](id);
    };
  }
  const module = { exports: {} };
  new Function("require", "module", "exports", bundle.outputFiles[0].text)(
    (path) => {
      if (path === "react") return runner.react;
      if (path.includes("sessionStore"))
        return {
          useSessionStore: { getState: () => ({ sessionContext: context }) },
        };
      if (path.includes("/api")) return api;
      throw new Error(`Unexpected import ${path}`);
    },
    module,
    module.exports,
  );
  let props = {
    courseId: C,
    lessonId: null,
    enabled: true,
    context: 1,
    pathname: `/course/${C}/edit`,
  };
  let courses = initial;
  let setCourses;
  const render = () => {
    [courses, setCourses] = runner.react.useState(initial);
    return module.exports.useCourseDetails({ ...props, courses, setCourses });
  };
  return {
    runner,
    calls,
    service,
    render: () => runner.render(render),
    update(next, commit = true) {
      props = { ...props, ...next };
      return runner.render(render, commit);
    },
    session(next) {
      context = next;
    },
    get courses() {
      return courses;
    },
    replace(next) {
      setCourses(next);
    },
  };
}

test("empty cache recovers course, modules and direct lesson without loops", async () => {
  const s = setup([]);
  s.service.getModuleBasicInfo = async (id) => ({ id, lessons: [{ id: L }] });
  s.render();
  s.update({ lessonId: L });
  await s.runner.flush();
  assert.deepEqual(s.calls, { course: [C], module: [M], lesson: [L] });
  assert.equal(s.courses[0].blocks[0].lessons[0].title, "detail");
  assert.equal(s.runner.value.loading, false);
  assert.equal(s.runner.value.error, "");
  await s.runner.flush();
  assert.equal(s.calls.module.length, 1);
});

test("failed module stays failed until explicit retry; successful sibling is retained", async () => {
  const s = setup([course([{ id: M }, { id: N }])]);
  s.service.getCourse = async () => course([{ id: M }, { id: N }]);
  let failing = true;
  const sibling = deferred();
  s.service.getModuleBasicInfo = async (id) => {
    if (id === N && failing) throw new Error("module failed");
    if (id === M) return sibling.promise;
    return { id, lessons: [], practice: [] };
  };
  s.render();
  await s.runner.flush();
  sibling.resolve({ id: M, lessons: [], practice: [] });
  await s.runner.flush();
  assert.equal(
    s.calls.module.filter((id) => id === N).length,
    1,
    "failed sibling retried automatically",
  );
  assert.match(s.runner.value.error, /module failed/);
  failing = false;
  s.runner.value.retry();
  await s.runner.flush();
  assert.equal(s.calls.module.filter((id) => id === N).length, 2);
  assert.equal(s.calls.module.filter((id) => id === M).length, 1);
  assert.equal(s.calls.course.length, 1);
  assert.equal(s.runner.value.error, "");
});

test("late course refs preserve loaded module lessons and do not hide module loading", async () => {
  const s = setup();
  const response = deferred();
  s.service.getCourse = () => response.promise;
  s.service.getModuleBasicInfo = async (id) => ({
    id,
    lessons: [{ id: L, title: "loaded" }],
    practice: [],
  });
  s.render();
  await s.runner.flush();
  assert.equal(s.runner.value.loading, true, "course is still pending");
  response.resolve(course([{ id: M, lessons: [], practice: [] }]));
  await s.runner.flush();
  assert.equal(s.courses[0].blocks[0].lessons[0].title, "loaded");
  assert.equal(s.calls.module.length, 1);
  assert.equal(s.runner.value.loading, false);
});

test("course success cannot clear a module error", async () => {
  const s = setup();
  const response = deferred();
  s.service.getCourse = () => response.promise;
  s.service.getModuleBasicInfo = async () => {
    throw new Error("module failed");
  };
  s.render();
  await s.runner.flush();
  response.resolve(course());
  await s.runner.flush();
  assert.match(s.runner.value.error, /module failed/);
  assert.equal(s.calls.module.length, 1);
});

for (const change of ["disable", "leave route", "unmount"]) {
  test(`${change} invalidates pending writes and chained lesson reads`, async () => {
    const s = setup();
    const response = deferred();
    s.service.getModuleBasicInfo = () => response.promise;
    s.render();
    s.update({ lessonId: L });
    await s.runner.flush();
    const before = s.courses;
    if (change === "disable") s.update({ enabled: false });
    else if (change === "leave route") s.update({ pathname: "/profile" });
    else s.runner.unmount();
    response.resolve({ id: M, lessons: [{ id: L, title: "stale" }] });
    await s.runner.flush();
    assert.equal(s.courses, before);
    assert.equal(s.calls.lesson.length, 0);
    if (change !== "unmount") {
      assert.equal(s.runner.value.loading, false);
      s.service.getModuleBasicInfo = async (id) => ({ id, lessons: [] });
      s.update({ enabled: true, pathname: `/course/${C}` });
      await s.runner.flush();
      assert.equal(s.calls.module.length, 2);
    }
  });
}

test("context switch before commit blocks stale apply and lesson continuation", async () => {
  const s = setup();
  const response = deferred();
  s.service.getModuleBasicInfo = () => response.promise;
  s.render();
  s.update({ lessonId: L });
  await s.runner.flush();
  s.session(2);
  const immediate = s.update({ context: 2, enabled: false }, false);
  assert.deepEqual(
    { loading: immediate.loading, error: immediate.error },
    { loading: false, error: "" },
  );
  response.resolve({ id: M, lessons: [{ id: L }] });
  // Resolve the old work without committing the new effects.
  for (let i = 0; i < 30; i++) await Promise.resolve();
  assert.equal(s.calls.lesson.length, 0);
  s.runner.commit();
  await s.runner.flush();
  assert.equal(s.courses[0].blocks[0].lessons, undefined);
});

test("A → B → A invalidates old same-course responses", async () => {
  const s = setup();
  const old = deferred();
  s.service.getCourse = () => old.promise;
  s.render();
  await s.runner.flush();
  s.update({ courseId: N, pathname: `/course/${N}` });
  s.service.getCourse = async (id) => ({ id, title: "new", blocks: [] });
  s.update({ courseId: C, pathname: `/course/${C}` });
  await s.runner.flush();
  old.resolve({ id: C, title: "stale", blocks: [] });
  await s.runner.flush();
  assert.equal(s.courses.find((item) => item.id === C).title, "new");
});

test("lesson navigation and course object changes do not refetch empty modules", async () => {
  const s = setup();
  s.render();
  await s.runner.flush();
  for (const mode of [
    "metrics",
    "edit",
    "lesson",
    "lessons",
    "practice",
    "block",
  ]) {
    s.update({ pathname: `/course/${C}/${mode}/${L}` });
    s.replace(s.courses.map((item) => ({ ...item, title: mode })));
    await s.runner.flush();
  }
  assert.deepEqual(s.calls, { course: [C], module: [M], lesson: [] });
});

test("course failure retries explicitly without refetching successful modules", async () => {
  const s = setup();
  let failing = true;
  s.service.getCourse = async () => {
    if (failing) throw new Error("course failed");
    return course();
  };
  s.render();
  await s.runner.flush();
  assert.match(s.runner.value.error, /course failed/);
  assert.equal(s.calls.course.length, 1);
  failing = false;
  s.runner.value.retry();
  await s.runner.flush();
  assert.equal(s.calls.course.length, 2);
  assert.deepEqual(s.calls.module, [M]);
  assert.equal(s.runner.value.error, "");
});

test("late course discovers new modules without repeating already loaded modules", async () => {
  const s = setup();
  const response = deferred();
  s.service.getCourse = () => response.promise;
  s.service.getModuleBasicInfo = async (id) => ({
    id,
    lessons: [{ id: id === M ? L : "other" }],
  });
  s.render();
  await s.runner.flush();
  response.resolve(course([{ id: M, lessons: [] }, { id: N }]));
  await s.runner.flush();
  assert.deepEqual(s.calls.module, [M, N]);
  assert.equal(s.courses[0].blocks[0].lessons[0].id, L);
  assert.equal(s.courses[0].blocks[1].lessons[0].id, "other");
  assert.equal(s.runner.value.loading, false);
});

test("old context rejection and retry callback cannot affect the new context", async () => {
  const s = setup();
  const response = deferred();
  s.service.getCourse = () => response.promise;
  s.render();
  await s.runner.flush();
  const oldRetry = s.runner.value.retry;
  s.session(2);
  s.service.getCourse = async () => ({ ...course(), title: "new context" });
  s.update({ context: 2 });
  await s.runner.flush();
  const count = s.calls.course.length;
  response.reject(new Error("old context failure"));
  oldRetry();
  await s.runner.flush();
  assert.equal(s.calls.course.length, count);
  assert.equal(s.runner.value.error, "");
  assert.equal(s.courses[0].title, "new context");
});

test("disable/re-enable while old response is pending starts a fresh same-key load", async () => {
  const s = setup();
  const response = deferred();
  s.service.getModuleBasicInfo = () => response.promise;
  s.render();
  await s.runner.flush();
  s.update({ enabled: false });
  s.service.getModuleBasicInfo = async (id) => ({
    id,
    lessons: [{ id: L, title: "new" }],
  });
  s.update({ enabled: true });
  await s.runner.flush();
  response.resolve({ id: M, lessons: [{ id: L, title: "old" }] });
  await s.runner.flush();
  assert.equal(s.courses[0].blocks[0].lessons[0].title, "new");
  assert.equal(s.calls.module.length, 2);
});

test("effect replay recovers pending work (StrictMode lifecycle)", async () => {
  const s = setup();
  s.render();
  s.runner.replayEffects();
  await s.runner.flush();
  assert.equal(s.runner.value.loading, false);
  assert.equal(s.runner.value.error, "");
  assert.deepEqual(s.calls.module, [M]);
});
