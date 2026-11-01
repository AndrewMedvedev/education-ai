import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";

import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const courseId = "11111111-1111-4111-8111-111111111111";
const lessonId = "22222222-2222-4222-8222-222222222222";
const otherLessonId = "33333333-3333-4333-8333-333333333333";
const structure = {
  id: courseId,
  title: "Course",
  creator_id: "author",
  blocks: [
    {
      id: "module",
      title: "Module",
      lessons: [
        { id: lessonId, title: "Lesson" },
        { id: otherLessonId, title: "Other" },
      ],
    },
  ],
};
const completed = {
  theoryCompletedAt: "done",
  practiceCompletedAt: "done",
  testCompletedAt: "done",
};
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

// A deterministic hook-lifecycle harness, not a DOM renderer. Only React's hook
// primitives and external dependencies are replaced; production hook bodies run.
function lifecycle() {
  let slots = [],
    index = 0,
    effects = [],
    dirty = false,
    renderFunction,
    value;
  const same = (a, b) =>
    a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
  const react = {
    useState(initial) {
      const i = index++;
      if (!slots[i])
        slots[i] = {
          value: typeof initial === "function" ? initial() : initial,
        };
      return [
        slots[i].value,
        (next) => {
          const result =
            typeof next === "function" ? next(slots[i].value) : next;
          if (!Object.is(result, slots[i].value)) {
            slots[i].value = result;
            dirty = true;
          }
        },
      ];
    },
    useRef(initial) {
      const i = index++;
      return (slots[i] ||= { current: initial });
    },
    useMemo(factory, deps) {
      const i = index++;
      if (!slots[i] || !same(slots[i].deps, deps))
        slots[i] = { value: factory(), deps };
      return slots[i].value;
    },
    useCallback(callback, deps) {
      return react.useMemo(() => callback, deps);
    },
    useEffect(effect, deps) {
      const i = index++;
      if (!slots[i] || !same(slots[i].deps, deps)) {
        const previous = slots[i];
        slots[i] = { deps };
        effects.push(() => {
          previous?.cleanup?.();
          slots[i].cleanup = effect();
        });
      }
    },
    createElement(type, props, ...children) {
      return { type, props: { ...props, children } };
    },
    Fragment: "fragment",
  };
  return {
    react,
    render(fn = renderFunction, commit = true) {
      renderFunction = fn;
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
      for (let i = 0; i < 30; i++) {
        await Promise.resolve();
        if (dirty) this.render();
      }
      return value;
    },
    unmount() {
      slots.forEach((slot) => slot?.cleanup?.());
      slots = [];
    },
    get value() {
      return value;
    },
  };
}

const hookBundle = await build({
  stdin: {
    contents: `export * from "./src/hooks/useCourseProgress.js";
    export * from "./src/hooks/useMyCoursesProgress.js";`,
    resolveDir: root,
  },
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  plugins: [
    {
      name: "hook-boundaries",
      setup(builder) {
        builder.onResolve(
          {
            filter:
              /^(react)$|\/services\/|\/stores\/sessionStore$|\/utils\/api$/,
          },
          ({ path }) => ({ path, external: true }),
        );
      },
    },
  ],
});

function setup() {
  const runner = lifecycle();
  let session = {
    sessionContext: 1,
    accessToken: "token",
    expiresAt: 9999999999,
  };
  const useSessionStore = (selector) => selector(session);
  useSessionStore.getState = () => session;
  const calls = { lessons: 0, theory: 0, sync: 0 };
  const service = {
    PROGRESS_STATUS: { COMPLETED: "completed", NOT_STARTED: "not_started" },
    getLessonProgressStatus: (record) =>
      record?.testCompletedAt ? "completed" : "not_started",
    getCourseLearningStructure: async () => structure,
    ensureCourseProgress: async () => ({ percent: 0 }),
    getCourseProgress: async () => ({ percent: 0 }),
    getLessonsProgress: async () => {
      calls.lessons++;
      return {};
    },
    ensureLessonProgress: async () => ({}),
    markLessonTheoryCompleted: async () => {
      calls.theory++;
      return completed;
    },
    syncCourseProgressPercent: async () => {
      calls.sync++;
      return { percent: 0 };
    },
    getLessonProgress: async () => completed,
  };
  const api = {
    hasSessionCredentials: (state) =>
      Boolean(state.accessToken || state.refreshToken),
    isUuid: (id) => /^[0-9a-f-]{36}$/.test(id),
  };
  const module = { exports: {} };
  new Function("require", "module", "exports", hookBundle.outputFiles[0].text)(
    (path) => {
      if (path === "react") return runner.react;
      if (path.includes("sessionStore")) return { useSessionStore };
      if (path.includes("/api")) return api;
      return service;
    },
    module,
    module.exports,
  );
  return {
    runner,
    service,
    calls,
    hooks: module.exports,
    setSession(next) {
      session = { ...session, ...next };
    },
  };
}

for (const outcome of ["resolve", "reject"]) {
  test(`course: stale track ${outcome} cannot affect another context with the same courseId`, async () => {
    const { runner, service, hooks, setSession } = setup();
    runner.render(() => hooks.useCourseProgress(courseId));
    await runner.flush();
    const oldCallback = runner.value.trackLesson;
    const request = deferred();
    service.ensureLessonProgress = () => request.promise;
    const pending = oldCallback("module", lessonId);
    setSession({ sessionContext: 2 });
    const immediate = runner.render(undefined, false);
    assert.deepEqual(immediate.lessonProgressById, {});
    assert.equal(immediate.summary.completed, 0);
    runner.commit();
    await runner.flush();
    request[outcome](
      outcome === "resolve" ? completed : new Error("old context"),
    );
    assert.equal(await pending, null);
    await runner.flush();
    assert.deepEqual(runner.value.lessonProgressById, {});
    assert.equal(runner.value.error, "");
    assert.equal(await oldCallback("module", lessonId), null);
    runner.unmount();
  });
}

test("course: loaded data is hidden synchronously and reloaded for the same course in a new context", async () => {
  const { runner, service, hooks, calls, setSession } = setup();
  service.getLessonsProgress = async () => {
    calls.lessons++;
    return { [lessonId]: completed };
  };
  runner.render(() => hooks.useCourseProgress(courseId));
  await runner.flush();
  assert.equal(runner.value.summary.completed, 1);
  setSession({ sessionContext: 2 });
  service.getLessonsProgress = async () => {
    calls.lessons++;
    return {};
  };
  const immediate = runner.render(undefined, false);
  assert.equal(immediate.summary.completed, 0);
  assert.equal(immediate.structure, null);
  assert.deepEqual(immediate.lessonProgressById, {});
  runner.commit();
  await runner.flush();
  assert.equal(calls.lessons, 2);
  assert.equal(runner.value.summary.completed, 0);
  runner.unmount();
});

test("course: logout blocks chained theory writes even before React commits cleanup", async () => {
  const { runner, service, calls, hooks, setSession } = setup();
  runner.render(() => hooks.useCourseProgress(courseId));
  await runner.flush();
  const request = deferred();
  service.ensureLessonProgress = () => request.promise;
  const pending = runner.value.completeTheory("module", lessonId);
  setSession({ sessionContext: 2, accessToken: null });
  request.resolve({});
  await pending;
  assert.equal(calls.theory, 0);
  runner.render();
  await runner.flush();
  assert.equal(runner.value.isEnabled, false);
  assert.deepEqual(runner.value.lessonProgressById, {});
  runner.unmount();
});

test("course: a late theory response does not overwrite the new learner's progress", async () => {
  const { runner, service, hooks, setSession } = setup();
  runner.render(() => hooks.useCourseProgress(courseId));
  await runner.flush();
  const request = deferred();
  service.markLessonTheoryCompleted = () => request.promise;
  const pending = runner.value.completeTheory("module", lessonId);
  await runner.flush();
  setSession({ sessionContext: 2 });
  runner.render();
  await runner.flush();
  request.resolve(completed);
  await pending;
  await runner.flush();
  assert.equal(runner.value.summary.completed, 0);
  assert.deepEqual(runner.value.lessonProgressById, {});
  runner.unmount();
});

test("course: late percent errors cannot enter the next context", async () => {
  const { runner, service, hooks, setSession } = setup();
  const request = deferred();
  service.syncCourseProgressPercent = () => request.promise;
  runner.render(() => hooks.useCourseProgress(courseId));
  await runner.flush();
  setSession({ sessionContext: 2 });
  service.syncCourseProgressPercent = async () => ({ percent: 0 });
  runner.render();
  await runner.flush();
  request.reject(new Error("old percent error"));
  await runner.flush();
  assert.equal(runner.value.error, "");
  runner.unmount();
});

test("course: late polling response is discarded after a context change", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const { runner, service, hooks, setSession } = setup();
  runner.render(() => hooks.useCourseProgress(courseId));
  await runner.flush();
  const request = deferred();
  service.getLessonProgress = () => request.promise;
  const pending = runner.value.refreshLesson(lessonId, "testCompletedAt");
  t.mock.timers.tick(800);
  await runner.flush();
  setSession({ sessionContext: 2 });
  runner.render();
  await runner.flush();
  request.resolve(completed);
  await pending;
  await runner.flush();
  assert.deepEqual(runner.value.lessonProgressById, {});
  runner.unmount();
});

test("course: disable/re-enable invalidates pending requests for the same course", async () => {
  const { runner, service, hooks } = setup();
  let enabled = true;
  runner.render(() => hooks.useCourseProgress(courseId, { enabled }));
  await runner.flush();
  const request = deferred();
  service.ensureLessonProgress = () => request.promise;
  const pending = runner.value.trackLesson("module", lessonId);
  enabled = false;
  runner.render();
  enabled = true;
  runner.render();
  await runner.flush();
  request.resolve(completed);
  assert.equal(await pending, null);
  await runner.flush();
  assert.deepEqual(runner.value.lessonProgressById, {});
  runner.unmount();
});

for (const outcome of ["resolve", "reject"]) {
  test(`profile: ignores stale summary ${outcome} with an unchanged course list`, async () => {
    const { runner, service, hooks, setSession } = setup();
    const request = deferred();
    service.getLessonsProgress = () => request.promise;
    runner.render(() => hooks.useMyCoursesProgress([{ id: courseId }]));
    await runner.flush();
    setSession({ sessionContext: 2 });
    service.getLessonsProgress = async () => ({});
    runner.render();
    await runner.flush();
    request[outcome](
      outcome === "resolve"
        ? { [lessonId]: completed }
        : new Error("old summary"),
    );
    await runner.flush();
    assert.equal(runner.value.isLoaded, true);
    assert.equal(runner.value.totals.completedLessons, 0);
    assert.deepEqual(runner.value.errorsByCourseId, {});
    runner.unmount();
  });
}

test("profile: loaded totals disappear on logout before effects run; no new requests", async () => {
  const { runner, service, hooks, calls, setSession } = setup();
  service.getLessonsProgress = async () => {
    calls.lessons++;
    return { [lessonId]: completed };
  };
  runner.render(() => hooks.useMyCoursesProgress([{ id: courseId }]));
  await runner.flush();
  assert.equal(runner.value.totals.completedLessons, 1);
  const count = calls.lessons;
  setSession({ sessionContext: 2, accessToken: null });
  const immediate = runner.render(undefined, false);
  assert.equal(immediate.totals.completedLessons, 0);
  assert.deepEqual(immediate.byCourseId, {});
  runner.commit();
  await runner.flush();
  assert.equal(calls.lessons, count);
  assert.equal(runner.value.isLoaded, false);
  runner.unmount();
});

test("profile: context change stops the old structure response from starting lesson reads", async () => {
  const { runner, service, hooks, calls, setSession } = setup();
  const request = deferred();
  service.getCourseLearningStructure = () => request.promise;
  runner.render(() => hooks.useMyCoursesProgress([{ id: courseId }]));
  setSession({ sessionContext: 2, accessToken: null });
  request.resolve(structure);
  await runner.flush();
  assert.equal(calls.lessons, 0);
  runner.unmount();
});

const viewerBundle = await build({
  entryPoints: [
    fileURLToPath(
      new URL("../components/course/CourseViewer.jsx", import.meta.url),
    ),
  ],
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  jsxFactory: "__jsx",
  jsxFragment: "__fragment",
  banner: {
    js: "const __jsx = require('react').createElement; const __fragment = require('react').Fragment;",
  },
  plugins: [
    {
      name: "viewer-boundaries",
      setup(builder) {
        builder.onResolve({ filter: /.*/ }, ({ path, kind }) =>
          kind === "entry-point" ? undefined : { path, external: true },
        );
      },
    },
  ],
});

function viewerSetup() {
  const { runner, service, setSession, hooks } = setup();
  let params = { courseId, lessonId };
  const session = {
    sessionContext: 1,
    accessToken: "token",
    expiresAt: 9999999999,
    identity: { id: "author" },
  };
  const useSessionStore = (selector) => selector(session);
  useSessionStore.getState = () => session;
  const store = (state) => (selector) => selector(state);
  const navigations = [];
  const components = new Map();
  const loadMyCourses = async () => ({ items: [], pages: 1 });
  const module = { exports: {} };
  const req = (path) => {
    if (path === "react") return runner.react;
    if (path === "react-router-dom")
      return {
        useParams: () => params,
        useNavigate: () => (url) => navigations.push(url),
      };
    if (path.endsWith(".css")) return {};
    if (path.includes("sessionStore")) return { useSessionStore };
    if (path.includes("permissionStore"))
      return {
        COURSE_PERMISSIONS: {},
        usePermissionStore: store({
          hasAnyPermission: () => true,
          hasPermission: () => true,
        }),
      };
    if (path.includes("studentStore"))
      return {
        useStudentStore: store({
          loadMyCourses,
          isCourseSigning: () => false,
        }),
      };
    if (path.includes("uiLayoutStore"))
      return {
        useUiLayoutStore: store({ getLessonActiveTab: () => "theory" }),
      };
    if (path.includes("useTheorySessionTracker"))
      return { useTheorySessionTracker() {} };
    if (path.includes("useCourseProgress")) return hooks;
    if (path.includes("courseService"))
      return {
        ...service,
        getCourseBasicInfo: async () => ({ ...structure, blocks: [] }),
        getLessonById: async (id) =>
          structure.blocks[0].lessons.find((lesson) => lesson.id === id),
        getLessonContentBlocks: async () => [],
      };
    if (path.includes("progressService"))
      return { getModuleProgressSummary: () => ({}) };
    if (path.includes("/api"))
      return {
        isTokenExpired: () => false,
        isUuid: (id) => /^[0-9a-f-]{36}$/.test(id),
      };
    if (path.includes("/errors"))
      return { getErrorMessage: (error) => error.message };
    const name = path.split("/").pop();
    const component = { name };
    components.set(name, component);
    return component;
  };
  new Function(
    "require",
    "module",
    "exports",
    viewerBundle.outputFiles[0].text,
  )(req, module, module.exports);
  const Viewer = module.exports.default;
  return {
    runner,
    service,
    navigations,
    render() {
      return runner.render(() => Viewer({}));
    },
    route(next) {
      params = { courseId, ...next };
    },
    context(next) {
      Object.assign(session, next);
      setSession(next);
    },
    find(name) {
      const visit = (node) => {
        if (!node || typeof node !== "object") return null;
        if (Array.isArray(node)) return node.map(visit).find(Boolean);
        if (node.type === components.get(name)) return node;
        return visit(node.props?.children);
      };
      return visit(runner.value);
    },
  };
}

test("viewer: direct lesson URL keeps structure even when basic info has no lessons", async () => {
  const viewer = viewerSetup();
  viewer.render();
  await viewer.runner.flush();
  assert.ok(
    viewer.find("LessonBasicInfo"),
    JSON.stringify(viewer.runner.value),
  );
  assert.equal(viewer.find("LessonBasicInfo").props.lesson.id, lessonId);
  assert.equal(
    viewer.find("CourseNavigationTree").props.selectedLessonId,
    lessonId,
  );
  viewer.runner.unmount();
});

test("viewer: navigation waits for URL, and back/forward immediately selects the URL lesson", async () => {
  const viewer = viewerSetup();
  viewer.render();
  await viewer.runner.flush();
  await viewer.find("CourseNavigationTree").props.openLesson(otherLessonId);
  await viewer.runner.flush();
  assert.deepEqual(viewer.navigations, [
    `/course/${courseId}/lesson/${otherLessonId}`,
  ]);
  assert.equal(viewer.find("LessonBasicInfo").props.lesson.id, lessonId);
  viewer.route({ lessonId: otherLessonId });
  viewer.render();
  assert.equal(viewer.find("LessonBasicInfo").props.lesson.id, otherLessonId);
  await viewer.runner.flush();
  viewer.route({ lessonId });
  viewer.render();
  assert.equal(viewer.find("LessonBasicInfo").props.lesson.id, lessonId);
  await viewer.runner.flush();
  viewer.runner.unmount();
});
