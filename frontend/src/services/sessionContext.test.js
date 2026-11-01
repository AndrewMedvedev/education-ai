import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";
import { fileURLToPath } from "node:url";

const { outputFiles } = await build({
  stdin: {
    contents: `export * as course from "./courseService.js";
      export * as progress from "./progressService.js";`,
    resolveDir: fileURLToPath(new URL("./", import.meta.url)),
  },
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  plugins: [
    {
      name: "service-boundaries",
      setup(builder) {
        builder.onResolve(
          { filter: /utils\/api$|studentApi$/ },
          ({ path }) => ({ path, external: true }),
        );
      },
    },
  ],
});

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const stale = { code: "STALE_SESSION" };
const statusError = (status) =>
  Object.assign(new Error(String(status)), { status });
const settle = async () => {
  for (let i = 0; i < 30; i++) await Promise.resolve();
};

function setup() {
  let context = 1;
  const counts = {};
  const handlers = {
    fetchCourses: async () => [],
    getCourseBasicInfo: async (id) => ({ id, blocks: [] }),
    getModuleBasicInfo: async (id) => ({ id, lessons: [] }),
    getLessonBasicInfo: async (id) => ({ id }),
    getLessonTheory: async () => [],
    fetchCourseProgress: async () => ({ id: "course-progress" }),
    fetchModuleProgress: async () => ({ id: "module-progress" }),
    fetchLessonProgress: async () => ({ id: "lesson-progress" }),
    createCourseProgress: async () => ({ id: "course-progress" }),
    createModuleProgress: async () => ({ id: "module-progress" }),
    createLessonProgress: async () => ({ id: "lesson-progress" }),
  };
  class ApiError extends Error {
    constructor(message, options) {
      super(message);
      Object.assign(this, options);
    }
  }
  const api = { ApiError, getSessionContext: () => context };
  for (const name of Object.keys(handlers)) {
    api[name] = (...args) => {
      counts[name] = (counts[name] || 0) + 1;
      return handlers[name](...args);
    };
  }
  const students = {
    getMyCourses: (...args) => handlers.getMyCourses(...args),
  };
  const module = { exports: {} };
  new Function("require", "module", "exports", outputFiles[0].text)(
    (path) => (path.endsWith("studentApi") ? students : api),
    module,
    module.exports,
  );
  return {
    ...module.exports,
    handlers,
    counts,
    changeContext() {
      context++;
    },
  };
}

const cacheCases = [
  [
    "getCourseBasicInfo",
    "getCourseBasicInfo",
    (title) => ({ id: "entity", title, blocks: [] }),
  ],
  [
    "getModuleById",
    "getModuleBasicInfo",
    (title) => ({ id: "entity", title, lessons: [] }),
  ],
  ["getLessonById", "getLessonBasicInfo", (title) => ({ id: "entity", title })],
  ["getLessonContentBlocks", "getLessonTheory", (title) => [{ title }]],
];
for (const [method, requestName, record] of cacheCases) {
  test(`course cache: ${method} reuses only the current context, including after logout/login`, async () => {
    const env = setup();
    const old = record("old");
    env.handlers[requestName] = async () => old;
    assert.deepEqual(await env.course[method]("entity"), old);
    assert.deepEqual(await env.course[method]("entity"), old);
    assert.equal(env.counts[requestName], 1);
    env.changeContext(); // logout
    const anonymous = record("anonymous");
    env.handlers[requestName] = async () => anonymous;
    assert.deepEqual(await env.course[method]("entity"), anonymous);
    env.changeContext(); // login, potentially the same user/tenant again
    const current = record("new login");
    env.handlers[requestName] = async () => current;
    assert.deepEqual(await env.course[method]("entity"), current);
    assert.equal(env.counts[requestName], 3);
  });

  test(`course cache: late ${method} completion cannot overwrite the next context's cache`, async () => {
    const env = setup();
    const request = deferred();
    env.handlers[requestName] = () => request.promise;
    const old = env.course[method]("entity");
    const rejected = assert.rejects(old, stale);
    env.changeContext();
    const current = record("new");
    env.handlers[requestName] = async () => current;
    assert.deepEqual(await env.course[method]("entity"), current);
    request.resolve(record("old"));
    await rejected;
    assert.deepEqual(await env.course[method]("entity"), current);
    assert.equal(env.counts[requestName], 2);
  });
}

test("course cache: a stale catalog response cannot populate any course entry", async () => {
  const env = setup();
  const request = deferred();
  env.handlers.fetchCourses = () => request.promise;
  const rejected = assert.rejects(env.course.getCourse("course"), stale);
  env.changeContext();
  request.resolve([
    { id: "course", title: "old" },
    { id: "other", title: "old" },
  ]);
  await rejected;
  assert.deepEqual(await env.course.getCourseBasicInfo("other"), {
    id: "other",
    blocks: [],
  });
  assert.equal(env.counts.getCourseBasicInfo, 1);
});

test("course cache: stale structure loading cannot merge modules into a new course or load the next module", async () => {
  const env = setup();
  const request = deferred();
  env.handlers.getCourseBasicInfo = async () => ({
    id: "course",
    blocks: [{ id: "module" }, { id: "next" }],
  });
  env.handlers.getModuleBasicInfo = () => request.promise;
  const rejected = assert.rejects(
    env.course.getCourseLearningStructure("course"),
    stale,
  );
  await settle();
  assert.equal(env.counts.getModuleBasicInfo, 1);
  env.changeContext();
  const current = { id: "course", blocks: [{ id: "module", title: "new" }] };
  env.handlers.getCourseBasicInfo = async () => current;
  await env.course.getCourseBasicInfo("course");
  request.resolve({
    id: "module",
    title: "old",
    lessons: [{ id: "old-lesson" }],
  });
  await rejected;
  assert.deepEqual(await env.course.getCourseBasicInfo("course"), current);
  assert.equal(env.counts.getModuleBasicInfo, 1);
});

test("course cache: even a cache-hit await cannot continue structure loading across contexts", async () => {
  const env = setup();
  env.handlers.getCourseBasicInfo = async () => ({
    id: "course",
    blocks: [{ id: "module" }],
  });
  await env.course.getCourseBasicInfo("course");
  const rejected = assert.rejects(
    env.course.getCourseLearningStructure("course"),
    stale,
  );
  env.changeContext();
  await rejected;
  assert.equal(env.counts.getModuleBasicInfo, undefined);
});

test("course cache: explicit invalidation still reloads course, module, lesson and theory", async () => {
  const env = setup();
  for (const [method] of cacheCases) await env.course[method]("entity");
  env.course.forgetCourseCache("entity", ["entity"], ["entity"]);
  for (const [method, requestName] of cacheCases) {
    await env.course[method]("entity");
    assert.equal(env.counts[requestName], 2);
  }
  env.course.forgetLessonTheory("entity");
  await env.course.getLessonById("entity");
  await env.course.getLessonContentBlocks("entity");
  assert.equal(env.counts.getLessonBasicInfo, 3);
  assert.equal(env.counts.getLessonTheory, 3);
});

test("course: stale enrollment pagination does not continue in the next context", async () => {
  const env = setup();
  const request = deferred();
  let reads = 0;
  env.handlers.getMyCourses = () => {
    reads++;
    return request.promise;
  };
  const rejected = assert.rejects(env.course.isUserEnrolled("course"), stale);
  env.changeContext();
  request.resolve({ items: [], page: 1, pages: 2 });
  await rejected;
  assert.equal(reads, 1);
});

const progressCases = [
  [
    "ensureCourseProgress",
    ["course"],
    "fetchCourseProgress",
    "createCourseProgress",
  ],
  [
    "ensureModuleProgress",
    ["course", "module"],
    "fetchModuleProgress",
    "createModuleProgress",
  ],
  [
    "ensureLessonProgress",
    ["course", "module", "lesson"],
    "fetchLessonProgress",
    "createLessonProgress",
  ],
];
for (const [method, args, readName, createName] of progressCases) {
  for (const outcome of ["resolve", "reject"]) {
    test(`progress: ${method} isolates promises and old ${outcome}/finally cannot evict the new flight`, async () => {
      const env = setup();
      const old = deferred();
      env.handlers[readName] = () => old.promise;
      const oldFlight = env.progress[method](...args);
      assert.equal(env.progress[method](...args), oldFlight);
      const rejected = assert.rejects(oldFlight);
      await settle();
      env.changeContext();
      const current = deferred();
      env.handlers[readName] = () => current.promise;
      const currentFlight = env.progress[method](...args);
      assert.notEqual(currentFlight, oldFlight);
      await settle();
      assert.equal(env.counts[readName], 2);
      old[outcome](
        outcome === "resolve" ? { id: "old" } : new Error("old failure"),
      );
      await rejected;
      assert.equal(env.progress[method](...args), currentFlight);
      assert.equal(env.counts[readName], 2);
      current.resolve({ id: "current" });
      assert.equal((await currentFlight).id, "current");
    });
  }

  test(`progress: ${method} cannot POST after a stale 404`, async () => {
    const env = setup();
    const request = deferred();
    env.handlers[readName] = () => request.promise;
    const rejected = assert.rejects(env.progress[method](...args), stale);
    await settle();
    env.changeContext();
    request.reject(statusError(404));
    await rejected;
    assert.equal(env.counts[createName], undefined);
  });

  test(`progress: ${method} cannot retry GET after a stale 409`, async () => {
    const env = setup();
    const request = deferred();
    env.handlers[readName] = async () => {
      throw statusError(404);
    };
    env.handlers[createName] = () => request.promise;
    const rejected = assert.rejects(env.progress[method](...args), stale);
    await settle();
    assert.equal(env.counts[createName], 1);
    env.changeContext();
    request.reject(statusError(409));
    await rejected;
    assert.equal(env.counts[readName], 1);
  });

  test(`progress: ${method} preserves same-context GET/404/POST/409/GET recovery`, async () => {
    const env = setup();
    env.handlers[readName] = async () => {
      if (env.counts[readName] === 1) throw statusError(404);
      return { id: "existing" };
    };
    env.handlers[createName] = async () => {
      throw statusError(409);
    };
    assert.equal((await env.progress[method](...args)).id, "existing");
    assert.equal(env.counts[readName], 2);
    assert.equal(env.counts[createName], 1);
  });
}

test("progress: old parent completion cannot start module or lesson work in the next context", async () => {
  const env = setup();
  const request = deferred();
  env.handlers.fetchCourseProgress = () => request.promise;
  const rejected = assert.rejects(
    env.progress.ensureLessonProgress("course", "module", "lesson"),
    stale,
  );
  env.changeContext();
  request.resolve({ id: "old-course-progress" });
  await rejected;
  assert.equal(env.counts.fetchModuleProgress, undefined);
  assert.equal(env.counts.fetchLessonProgress, undefined);
});

test("progress: context change stops the lesson batch queue, without reporting stale data as missing progress", async () => {
  const env = setup();
  const request = deferred();
  env.handlers.fetchLessonProgress = () => request.promise;
  const errors = [];
  const rejected = assert.rejects(
    env.progress.getLessonsProgress(["one", "two", "three", "four", "five"], {
      onError: (error) => errors.push(error),
    }),
    stale,
  );
  assert.equal(env.counts.fetchLessonProgress, 4);
  env.changeContext();
  request.resolve({ id: "old" });
  await rejected;
  assert.equal(env.counts.fetchLessonProgress, 4);
  assert.deepEqual(errors, []);
});
