import test from "node:test";
import assert from "node:assert/strict";
import { create } from "zustand";
import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import {
  createDraftDebounce,
  createScopedStorage,
  reloadScope,
} from "./reloadPersistence.js";
import { restoreRouteScroll } from "../hooks/routeScrollRestoration.js";

const context = {
  accessToken: "not-persisted",
  identity: { id: "user" },
  membershipId: "member",
  organizationId: "org",
  sessionContext: 1,
};
const memory = () => {
  const data = new Map();
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
  };
};
function clock() {
  let sequence = 0;
  const tasks = new Map();
  return {
    tasks,
    setTimeout(fn) {
      tasks.set(++sequence, fn);
      return sequence;
    },
    clearTimeout(id) {
      tasks.delete(id);
    },
    run() {
      const pending = [...tasks.values()];
      tasks.clear();
      pending.forEach((fn) => fn());
    },
  };
}

test("scope requires confirmed identity and all tenant IDs; legacy data is never adopted", () => {
  const storage = memory();
  storage.setItem("chats", "legacy-private-data");
  let state = { ...context, identity: null };
  const scoped = createScopedStorage(
    () => storage,
    () => reloadScope(state),
  );
  assert.equal(scoped.getItem("chats"), null);
  scoped.setItem("chats", "ignored");
  state = context;
  assert.equal(scoped.getItem("chats"), null);
  scoped.setItem("chats", "mine");
  for (const change of [
    { identity: { id: "other" } },
    { membershipId: "other" },
    { organizationId: "other" },
  ]) {
    state = { ...context, ...change };
    assert.equal(scoped.getItem("chats"), null);
  }
  state = context;
  assert.equal(scoped.getItem("chats"), "mine");
  assert.equal(storage.getItem("chats"), "legacy-private-data");
  assert.equal(reloadScope({ ...context, organizationId: null }), null);
});

test("blocked storage reports read/write failure without breaking a dialog", () => {
  const reports = [];
  const scoped = createScopedStorage(
    () => {
      throw Error("denied");
    },
    () => "scope",
    (event) => reports.push(event),
  );
  assert.equal(scoped.getItem("x"), null);
  assert.equal(scoped.setItem("x", "value"), false);
  assert.equal(scoped.removeItem("x"), false);
  assert.deepEqual(
    reports.map((event) => event.method),
    ["getItem", "setItem", "removeItem"],
  );
  assert.ok(reports.every((event) => event.error && event.scope === "scope"));
  const unavailable = createScopedStorage(
    () => null,
    () => "scope",
    (event) => reports.push(event),
  );
  assert.equal(unavailable.setItem("x", "value"), false);
  assert.equal(reports.length, 4);
});

test("draft debounce flush is synchronous, cancels its timer and writes the latest edit once", () => {
  const timers = clock();
  let draft = "first";
  const saved = [];
  const debounce = createDraftDebounce(() => saved.push(draft), 450, timers);
  debounce.schedule();
  draft = "latest";
  debounce.schedule();
  assert.equal(timers.tasks.size, 1);
  debounce.flush();
  assert.deepEqual(saved, ["latest"]);
  timers.run();
  assert.deepEqual(saved, ["latest"]);
  debounce.schedule();
  debounce.cancel();
  timers.run();
  assert.deepEqual(saved, ["latest"]);
});

function scrollWindow() {
  const timers = clock();
  const listeners = new Map();
  return {
    ...timers,
    scrollY: 0,
    max: 10,
    requestAnimationFrame: timers.setTimeout,
    cancelAnimationFrame: timers.clearTimeout,
    addEventListener(name, fn) {
      listeners.set(name, fn);
    },
    removeEventListener(name) {
      listeners.delete(name);
    },
    scrollTo({ top }) {
      this.scrollY = Math.min(top, this.max);
    },
    interrupt() {
      listeners.get("wheel")?.();
    },
  };
}

test("scroll reload waits for async content and stops on navigation/user input", () => {
  const win = scrollWindow();
  let finished = 0;
  const stop = restoreRouteScroll(900, win, () => finished++);
  win.run();
  assert.equal(finished, 0);
  win.max = 2000;
  win.run();
  assert.equal(win.scrollY, 900);
  assert.equal(finished, 1);
  stop();
  assert.equal(finished, 1);
  restoreRouteScroll(1800, win, () => finished++);
  win.interrupt();
  win.run();
  assert.equal(win.scrollY, 900);
  assert.equal(finished, 2);
  const cancel = restoreRouteScroll(1900, win, () => finished++);
  cancel();
  win.run();
  assert.equal(win.scrollY, 900);
});

// Exercise the actual stores, replacing only session/network/browser boundaries.
async function stores({ views = false, storage = memory(), api = {} } = {}) {
  const timers = clock();
  const listeners = new Map();
  globalThis.window = {
    ...timers,
    localStorage: storage,
    addEventListener: (event, fn) => listeners.set(event, fn),
    removeEventListener: (event) => listeners.delete(event),
    matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
    requestAnimationFrame: (fn) => { fn(); return 1; },
    cancelAnimationFrame() {},
  };
  globalThis.document = {
    visibilityState: "visible",
    addEventListener: (event, fn) => listeners.set(event, fn),
  };
  const session = create(() => context);
  const effects = [];
  let rendering = null;
  const hooks = {
    useEffect: (effect, deps) => rendering ? rendering.effect(effect, deps) : effects.push(effect),
    useLayoutEffect: (effect, deps) => rendering ? rendering.effect(effect, deps) : effects.push(effect),
    useRef: (current) => rendering ? rendering.ref(current) : ({ current }),
    useState: (initial) => rendering ? rendering.state(initial) : [
      typeof initial === "function" ? initial() : initial,
      () => {},
    ],
    useMemo: (fn, deps) => rendering ? rendering.memo(fn, deps) : fn(),
    useCallback: (fn) => fn,
    useSyncExternalStore: (_subscribe, snapshot) => snapshot(),
    useDebugValue: () => {},
    createElement: (type, props) => ({ type, props }),
  };
  globalThis.__reloadHarness = { session, api, hooks };
  window.setInterval = timers.setTimeout;
  window.clearInterval = timers.clearTimeout;
  const names = [
    "convertDocumentToMarkdown",
    "askEditorAgent",
    "askInterviewerAgent",
    "askLessonInterviewerAgent",
    "askMentorAgent",
    "askModuleInterviewerAgent",
    "assignLessonToModule",
    "createCourse",
    "createLesson",
    "createModule",
    "deleteLesson",
    "deleteModule",
    "getCourseBasicInfo",
    "isAuthenticated",
    "redirectToLogin",
    "updateCourse",
    "updateLesson",
    "updateLessonContentBlocks",
    "updateModule",
    "uploadDocument",
    "fetchCourseStatus",
    "saveDocument",
    "getModuleBasicInfo",
    "getLessonBasicInfo",
    "DOCUMENT_ALLOWED_EXTENSION",
    "DOCUMENT_ALLOWED_EXTENSIONS_LABEL",
    "DOCUMENT_MAX_SIZE_BYTES",
  ];
  const result = await build({
    stdin: {
      contents:
        'export { useAgentStore } from "../stores/agentStore.js"; export { useGenerationJobsStore } from "../stores/generationJobsStore.js"; export { useDndCourseStore } from "../dnd-course/store.js"; export { loadDraft, pickDraft, saveDraft } from "../dnd-course/draft.js"; export { scopedReloadStorage, getReloadStorage, useReloadStorageErrors } from "./reloadScope.js";' +
        (views
          ? 'export { default as LessonAiChat } from "../components/LessonAiChat.jsx"; export { default as LessonContentEditor } from "../components/LessonContentEditor.jsx"; export { default as ReloadStorageWarning } from "./ReloadStorageWarning.jsx"; export { default as StartScreen } from "../dnd-course/StartScreen.jsx"; export { default as TopBar } from "../dnd-course/TopBar.jsx"; export { default as AgentInterviewDialog } from "../components/editor/AgentInterviewDialog.jsx"; export { default as CreatorChatView } from "../components/CreatorChatView.jsx"; export { useGenerationJobsWatcher } from "../hooks/useGenerationJobsWatcher.js";'
          : ""),
      resolveDir: fileURLToPath(new URL(".", import.meta.url)),
    },
    bundle: true,
    write: false,
    platform: "node",
    format: "esm",
    define: { "import.meta.env": "{}" },
    jsx: "automatic",
    loader: { ".css": "empty" },
    plugins: [
      {
        name: "boundaries",
        setup(builder) {
          if (views) {
            builder.onResolve(
              {
                filter:
                  /^(react|react\/jsx-runtime|react-router-dom|react-markdown|remark-gfm)$/,
              },
              (args) => ({ path: args.path, namespace: "view" }),
            );
            builder.onResolve(
              {
                filter:
                  /(?:ui\/(?:ConfirmDialog|AppModal|FloatingWindow)|services\/courseService)$/,
              },
              (args) => ({ path: args.path, namespace: "view" }),
            );
            builder.onLoad({ filter: /.*/, namespace: "view" }, ({ path }) => ({
              contents:
                path === "react"
                  ? "const h = globalThis.__reloadHarness.hooks; export default h; export const { useEffect, useLayoutEffect, useRef, useState, useMemo, useCallback, useSyncExternalStore, useDebugValue, createElement } = h; export const createContext = (value) => ({value}); export const useContext = (context) => context.value; export const useId = () => 'test-id'; export const Fragment = 'fragment';"
                  : path === "react/jsx-runtime"
                    ? 'export const jsx = (type, props) => ({type, props}); export const jsxs = jsx; export const Fragment = "fragment";'
                    : path === "react-router-dom"
                      ? "export const useNavigate = () => () => {};"
                      : path.endsWith("courseService")
                        ? "export const forgetCourseCache = () => {};"
                        : "export default () => null;",
            }));
          }
          builder.onResolve(
            {
              filter: /(?:sessionStore|utils\/api|agentMockHook|serverCourse)$/,
            },
            (args) => ({ path: args.path, namespace: "mock" }),
          );
          builder.onLoad({ filter: /.*/, namespace: "mock" }, ({ path }) => ({
            contents: path.endsWith("sessionStore")
              ? "const s = globalThis.__reloadHarness.session; export const useSessionStore = Object.assign((selector) => selector(s.getState()), s);"
              : path.endsWith("agentMockHook")
                ? "export const isAgentMockEnabled = () => false; export const mockInterviewer = () => {};"
                : path.endsWith("serverCourse")
                  ? "export const fetchCourseStructure = (...args) => globalThis.__reloadHarness.api.fetchCourseStructure(...args); export const fetchLessonBlocks = async () => [];"
                  : names
                      .map(
                        (name) =>
                          `export const ${name} = (...args) => globalThis.__reloadHarness.api.${name}?.(...args);`,
                      )
                      .join("\n"),
          }));
        },
      },
    ],
  });
  let module;
  try {
    module = await import(
      `data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}#${Math.random()}`
    );
  } catch (error) {
    throw new Error(error.message);
  }
  return {
    ...module,
    session,
    api,
    storage,
    timers,
    listeners,
    renderer(component) {
      const slots = [];
      let index = 0;
      const same = (a, b) => a && b && a.length === b.length && a.every((value, i) => Object.is(value, b[i]));
      const instance = {
        state(initial) {
          const slot = index++;
          if (!(slot in slots)) slots[slot] = typeof initial === "function" ? initial() : initial;
          return [slots[slot], (value) => { slots[slot] = typeof value === "function" ? value(slots[slot]) : value; }];
        },
        ref(initial) { return instance.state(() => ({ current: initial }))[0]; },
        memo(fn, deps) {
          const slot = index++;
          if (!same(slots[slot]?.deps, deps)) slots[slot] = { deps, value: fn() };
          return slots[slot].value;
        },
        effect(fn, deps) {
          const slot = index++;
          if (same(slots[slot]?.deps, deps)) return;
          slots[slot]?.cleanup?.();
          const entry = { deps };
          slots[slot] = entry;
          effects.push(() => { entry.cleanup = fn(); });
        },
      };
      return {
        render(props) {
          index = 0;
          rendering = instance;
          try { return component(props); } finally { rendering = null; }
        },
        unmount() { slots.forEach((slot) => slot?.cleanup?.()); },
      };
    },
    mountEffects() {
      const cleanup = effects
        .splice(0)
        .map((effect) => effect())
        .filter((fn) => typeof fn === "function");
      return () => cleanup.forEach((fn) => fn());
    },
  };
}

test("actual stores restore chat_id/jobs without POST, isolate tenants, and reject late AI responses", async () => {
  const s = await stores();
  const agent = s.useAgentStore;
  agent.getState().initializeConversation({
    key: "chat",
    agent: "interviewer",
    courseId: "course",
  });
  agent.getState().setChatId("chat", "backend-chat");
  agent.getState().appendMessage("chat", "assistant", "private");
  agent.getState().setCreatorDraft("chat", {
    stepIndex: 2,
    answers: { goal: "learn" },
    inputValue: "unsent",
  });
  s.useGenerationJobsStore.getState().startJob({
    key: "job",
    kind: "module",
    courseId: "course",
    taskId: "task",
  });
  // A full in-memory reset followed by rehydrate is the reload contract.
  agent.persist.setOptions({
    storage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  });
  agent.setState({ conversations: {}, generations: {}, creatorDrafts: {} });
  // The scoped payload is retained; reloading a fresh store reads it without networking.
  const records = [...s.storage.data.values()].map((value) =>
    JSON.parse(value),
  );
  assert.equal(
    records.find((record) => record.state.conversations)?.state.conversations
      .chat.chatId,
    "backend-chat",
  );
  assert.equal(Object.keys(s.api).length, 0);
  // Re-enable using another store's compatible JSON adapter.
  agent.persist.setOptions({
    storage: s.useGenerationJobsStore.persist.getOptions().storage,
  });
  await agent.persist.rehydrate();
  assert.equal(agent.getState().conversations.chat.chatId, "backend-chat");
  assert.equal(agent.getState().creatorDrafts.chat.inputValue, "unsent");
  let resolve;
  s.api.askInterviewerAgent = () =>
    new Promise((done) => {
      resolve = done;
    });
  const pending = agent.getState().sendMessage({
    key: "chat",
    agent: "interviewer",
    courseId: "course",
    content: "launch",
  });
  s.session.setState({ identity: { id: "other" }, sessionContext: 2 });
  assert.deepEqual(agent.getState().conversations, {});
  assert.deepEqual(s.useGenerationJobsStore.getState().jobs, {});
  resolve({ chatId: "old", content: "late" });
  assert.equal(await pending, null);
  assert.deepEqual(agent.getState().conversations, {});
  s.session.setState({ ...context, sessionContext: 3 });
  assert.equal(agent.getState().conversations.chat.chatId, "backend-chat");
  assert.equal(agent.getState().conversations.chat.status, "idle");
  assert.equal(s.useGenerationJobsStore.getState().jobs.job.taskId, "task");
});

test("DnD pagehide flush saves latest draft without File or network; reload marks interrupted upload", async () => {
  const s = await stores();
  const dnd = s.useDndCourseStore;
  dnd.getState().hydrate();
  dnd.getState().setCourseForm({ title: "Latest draft" });
  dnd.setState({
    materials: [
      {
        id: "material",
        fileName: "notes.txt",
        status: "uploading",
        file: {
          toJSON() {
            throw Error("File must not be serialized");
          },
        },
      },
    ],
  });
  s.listeners.get("pagehide")();
  assert.equal(s.timers.tasks.size, 0);
  assert.equal(Object.keys(s.api).length, 0);
  const restored = s.loadDraft().draft;
  assert.equal(restored.courseForm.title, "Latest draft");
  assert.equal(restored.materials[0].status, "error");
  assert.equal(restored.materials[0].interrupted, true);
  assert.equal("file" in restored.materials[0], false);
  assert.equal(s.saveDraft(restored), true);
  const twice = s.loadDraft().draft.materials[0];
  assert.equal(twice.interrupted, true);
  assert.match(twice.error, /повторно/);
  s.session.setState({ organizationId: "other-org", sessionContext: 2 });
  assert.equal(dnd.getState().courseForm.title, "");
  s.session.setState({ ...context, sessionContext: 3 });
  assert.equal(dnd.getState().courseForm.title, "Latest draft");
  dnd.getState().setCourseForm({ title: "Not yet debounced" });
  s.session.setState({ organizationId: "other-org", sessionContext: 4 });
  s.session.setState({ ...context, sessionContext: 5 });
  assert.equal(dnd.getState().courseForm.title, "Not yet debounced");
});

test("Creator reload resumes GET only and ignores status after unmount", async () => {
  const s = await stores({ views: true });
  let posts = 0;
  let gets = 0;
  let resolveStatus;
  s.api.askInterviewerAgent = () => {
    posts++;
  };
  s.api.fetchCourseStatus = () => {
    gets++;
    return new Promise((resolve) => {
      resolveStatus = resolve;
    });
  };
  s.scopedReloadStorage.setItem("course-generation:active-course", "course");
  s.scopedReloadStorage.setItem(
    "course-generation:course",
    JSON.stringify({
      courseId: "course",
      generatedCourseId: "generated",
      chatId: "chat",
      taskId: "task",
      generationStartedAt: new Date().toISOString(),
    }),
  );
  const view = s.CreatorChatView();
  view.type();
  const unmount = s.mountEffects();
  assert.equal(posts, 0);
  assert.equal(gets, 1);
  const snapshot = s.useAgentStore.getState().generations;
  unmount();
  resolveStatus({ status: "draft" });
  await new Promise(setImmediate);
  assert.equal(posts, 0);
  assert.equal(s.timers.tasks.size, 0);
  assert.equal(s.useAgentStore.getState().generations, snapshot);
});

test("generation watcher cannot deliver late results or complete a replacement job", async () => {
  const s = await stores({ views: true });
  let resolveModule;
  let delivered = 0;
  let done = 0;
  s.api.getModuleBasicInfo = () =>
    new Promise((resolve) => {
      resolveModule = resolve;
    });
  s.useGenerationJobsStore.getState().startJob({
    key: "job",
    kind: "module",
    courseId: "course",
    resultId: "module",
  });
  s.useGenerationJobsWatcher({
    onModule: () => delivered++,
    onDone: () => done++,
  });
  const unmount = s.mountEffects();
  s.session.setState({ identity: { id: "other" }, sessionContext: 2 });
  s.useGenerationJobsStore
    .getState()
    .startJob({ key: "job", kind: "module", courseId: "course" });
  resolveModule({ id: "module", lessons: [{ id: "old-private-lesson" }] });
  await new Promise(setImmediate);
  assert.equal(delivered, 0);
  assert.equal(done, 0);
  assert.equal(s.useGenerationJobsStore.getState().jobs.job.resultId, null);
  unmount();
});

test("DnD late server load is rejected even after A -> B -> A; late save cannot restore old course", async () => {
  const s = await stores();
  let resolveLoad;
  s.api.fetchCourseStructure = () =>
    new Promise((resolve) => {
      resolveLoad = resolve;
    });
  const pending = s.useDndCourseStore.getState().loadFromServer("old-course");
  s.session.setState({ identity: { id: "other" }, sessionContext: 2 });
  s.session.setState({ ...context, sessionContext: 3 });
  resolveLoad({ course: { id: "old-course", title: "Private" }, modules: [] });
  await pending;
  assert.equal(s.useDndCourseStore.getState().course, null);
  const dnd = s.useDndCourseStore;
  dnd.setState({
    course: {
      id: "old-course",
      title: "Private",
      description: "Old",
      tags: [],
    },
  });
  let resolveSave;
  s.api.updateCourse = () =>
    new Promise((resolve) => {
      resolveSave = resolve;
    });
  const save = dnd.getState().saveCourse();
  s.session.setState({ identity: { id: "other" }, sessionContext: 4 });
  resolveSave({ id: "old-course", title: "Private" });
  await save;
  assert.equal(dnd.getState().course, null);
});

function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (!tree || typeof tree !== "object") return [];
  return [tree, ...nodes(tree.props?.children)];
}
function warningIn(s, tree) {
  const banner = nodes(tree).find((node) => node.type === s.ReloadStorageWarning);
  assert.ok(banner, "view must render the storage warning component");
  return banner.type(banner.props);
}

test("quota failures are visible in Creator and both DnD phases; unrelated reads/writes cannot hide them", async () => {
  const s = await stores({ views: true });
  const setItem = s.storage.setItem;
  s.storage.setItem = () => { throw new DOMException("full", "QuotaExceededError"); };
  const agent = s.useAgentStore;
  agent.getState().setCreatorDraft("draft", { inputValue: "keep in memory" });
  assert.equal(agent.getState().creatorDrafts.draft.inputValue, "keep in memory");
  const view = s.CreatorChatView();
  assert.equal(warningIn(s, view.type()).props.role, "alert");
  s.useDndCourseStore.getState().hydrate();
  s.useDndCourseStore.getState().setCourseForm({ title: "unsaved local title" });
  s.listeners.get("pagehide")();
  assert.equal(s.saveDraft(s.useDndCourseStore.getState()), false);
  assert.equal(warningIn(s, s.StartScreen()).props.role, "alert");
  assert.equal(warningIn(s, s.TopBar({})).props.role, "alert");
  assert.equal(s.useDndCourseStore.getState().courseForm.title, "unsaved local title");
  s.storage.setItem = setItem;
  s.scopedReloadStorage.getItem("ai-course-agent-chats-v1");
  s.scopedReloadStorage.setItem("course-generation:active-course", "other-key");
  assert.ok(s.ReloadStorageWarning({ names: ["ai-course-agent-chats-v1"] }));
  const oldScope = reloadScope(context);
  s.session.setState({ organizationId: "new-org", sessionContext: 2 });
  assert.equal(s.ReloadStorageWarning({ names: ["ai-course-agent-chats-v1"] }), null);
  s.storage.setItem = () => { throw Error("denied"); };
  assert.equal(s.getReloadStorage(oldScope).setItem("private-draft", "x"), false);
  assert.equal(s.ReloadStorageWarning({ names: ["private-draft"] }), null);
  s.storage.setItem = setItem;
  s.session.setState({ ...context, sessionContext: 3 });
  agent.getState().setCreatorDraft("draft", { inputValue: "saved now" });
  assert.equal(s.ReloadStorageWarning({ names: ["ai-course-agent-chats-v1"] }), null);
  assert.equal(s.saveDraft(s.useDndCourseStore.getState()), true);
  assert.equal(warningIn(s, s.StartScreen()), null);
});

test("AgentInterview input persists synchronously, restores without POST, and is scoped by user and entity", async () => {
  const s = await stores({ views: true });
  let posts = 0;
  s.api.askModuleInterviewerAgent = () => { posts++; };
  s.api.askLessonInterviewerAgent = () => { posts++; };
  const props = { open: true, kind: "module", courseId: "course" };
  const render = (props) => { const view = s.AgentInterviewDialog(props); return view.type(view.props); };
  const input = (tree) => nodes(tree).find((node) => node.type === "textarea");
  const first = input(render(props));
  assert.ok(first);
  first.props.onChange({ target: { value: "module draft" } });
  assert.ok([...s.storage.data.values()].some((value) => value.includes("module draft")));
  const saved = s.scopedReloadStorage.getItem("ai-course-agent-chats-v1");
  s.useAgentStore.setState({ interviewDrafts: {} });
  s.scopedReloadStorage.setItem("ai-course-agent-chats-v1", saved);
  s.useAgentStore.persist.rehydrate();
  assert.equal(input(render(props)).props.value, "module draft");
  assert.equal(input(render({ ...props, courseId: "another" })).props.value, "");
  assert.equal(input(render({ ...props, kind: "lesson", moduleId: "m1" })).props.value, "");
  s.session.setState({ identity: { id: "other-user" }, sessionContext: 2 });
  assert.equal(input(render(props)).props.value, "");
  first.props.onChange({ target: { value: "stale callback" } });
  assert.equal(input(render(props)).props.value, "");
  s.session.setState({ ...context, sessionContext: 3 });
  assert.equal(input(render(props)).props.value, "module draft");
  assert.equal(posts, 0);
});

test("Creator reload retains only file metadata and displays explicit reselect notice", async () => {
  const { creatorFileMetadata, needsFileReselection, RESELECT_CREATOR_FILES } = await import("./creatorFileDraft.js");
  const metadata = creatorFileMetadata([{ id: "f", name: "notes.txt", sizeKb: 1, size: 42, lastModified: 123,
    file: { toJSON() { throw Error("never serialize File"); } } }]);
  assert.equal(needsFileReselection(metadata), true);
  assert.equal("file" in metadata[0], false);
  assert.equal(JSON.parse(JSON.stringify(metadata))[0].size, 42);
  const s = await stores({ views: true });
  s.scopedReloadStorage.setItem("course-generation:active-course", "course");
  s.useAgentStore.getState().setCreatorDraft("interviewer:course:", { inputValue: "unsent", files: metadata });
  const view = s.CreatorChatView();
  const tree = view.type();
  assert.ok(nodes(tree).some((node) => node.props?.role === "alert" && node.props.children === RESELECT_CREATOR_FILES));
  assert.ok(nodes(tree).some((node) => Array.isArray(node.props?.children) && node.props.children.includes("notes.txt")));
});

test("agent v1 migration is scoped and bounded; editor/mentor reload history and chat_id without POST", async () => {
  const storage = memory();
  const scoped = createScopedStorage(() => storage, () => reloadScope(context));
  const conversations = Object.fromEntries(Array.from({ length: 33 }, (_, i) => [`chat-${i}`, {
    agent: i === 32 ? "mentor" : "editor", courseId: "course", chatId: `server-${i}`,
    messages: Array.from({ length: 205 }, (_, j) => ({ id: `${j}`, role: j % 2 ? "assistant" : "user", text: `message-${j}` })),
    status: "loading", activeRequestId: 123,
  }]));
  scoped.setItem("ai-course-agent-chats-v1", JSON.stringify({ version: 1, state: {
    conversations,
    interviewDrafts: Object.fromEntries(Array.from({ length: 35 }, (_, i) => [`input-${i}`, "x".repeat(10001)])),
  } }));
  storage.setItem("ai-course-agent-chats-v1", JSON.stringify({ version: 1, state: { conversations: {
    foreign: { agent: "mentor", messages: [{ text: "global secret" }] },
  } } }));
  let posts = 0;
  const api = { askEditorAgent: () => { posts++; }, askMentorAgent: () => { posts++; } };
  const s = await stores({ storage, api });
  const state = s.useAgentStore.getState();
  assert.equal(Object.keys(state.conversations).length, 30);
  assert.equal(state.conversations["chat-0"], undefined);
  for (const i of [31, 32]) {
    const chat = state.conversations[`chat-${i}`];
    assert.equal(chat.chatId, `server-${i}`);
    assert.equal(chat.messages.length, 200);
    assert.equal(chat.messages[0].text, "message-5");
    assert.equal(chat.status, "idle");
    assert.equal(chat.activeRequestId, null);
  }
  assert.equal(Object.keys(state.interviewDrafts).length, 30);
  assert.equal(state.interviewDrafts["input-34"].length, 10000);
  assert.equal(state.conversations.foreign, undefined);
  assert.equal(JSON.parse(scoped.getItem("ai-course-agent-chats-v1")).version, 2);
  const fresh = await stores({ storage, api });
  assert.equal(fresh.useAgentStore.getState().conversations["chat-32"].chatId, "server-32");
  fresh.session.setState({ organizationId: "other", sessionContext: 2 });
  assert.deepEqual(fresh.useAgentStore.getState().conversations, {});
  assert.deepEqual(fresh.useAgentStore.getState().interviewDrafts, {});
  assert.equal(posts, 0);
});

test("mentor input/history reload without POST or notification; stale send/input callbacks are rejected", async () => {
  const s = await stores({ views: true });
  let posts = 0;
  let notified = 0;
  s.api.askMentorAgent = async () => { posts++; return { chatId: "mentor-server", content: "answer" }; };
  const props = { courseId: "course", lessonId: "lesson", isOpen: true, onAssistantResponse: () => notified++ };
  const view = s.LessonAiChat(props);
  const runtime = s.renderer(view.type);
  const render = () => runtime.render(props);
  const input = (tree) => nodes(tree).find((node) => node.type === "textarea");
  let tree = render(); s.mountEffects();
  input(tree).props.onChange({ target: { value: "mentor unsent" } });
  tree = render();
  assert.equal(input(tree).props.value, "mentor unsent");
  const oldInput = input(tree);
  const oldSend = nodes(tree).find((node) => node.props?.className === "lesson-ai-send");
  const setItem = s.storage.setItem;
  s.storage.setItem = () => { throw Error("quota"); };
  oldInput.props.onChange({ target: { value: "mentor retained in memory" } });
  assert.equal(warningIn(s, render()).props.role, "alert");
  s.storage.setItem = setItem;
  input(render()).props.onChange({ target: { value: "mentor unsent" } });
  s.useAgentStore.getState().appendMessage("mentor:course:lesson", "assistant", "stored history");
  s.useAgentStore.getState().setChatId("mentor:course:lesson", "stored-chat");
  runtime.unmount();
  oldInput.props.onChange({ target: { value: "after unmount" } });
  await oldSend.props.onClick();
  assert.equal(posts, 0);
  const reloaded = await stores({ views: true, storage: s.storage, api: s.api });
  const nextView = reloaded.LessonAiChat({ ...props, isOpen: false });
  const next = reloaded.renderer(nextView.type);
  const restored = next.render({ ...props, isOpen: false }); reloaded.mountEffects();
  assert.equal(input(restored).props.value, "mentor unsent");
  assert.ok(JSON.stringify(restored).includes("stored history"));
  assert.equal(posts, 0);
  assert.equal(notified, 0);
  reloaded.session.setState({ identity: { id: "other" }, sessionContext: 2 });
  input(restored).props.onChange({ target: { value: "foreign" } });
  await nodes(restored).find((node) => node.props?.className === "lesson-ai-send").props.onClick();
  assert.deepEqual(reloaded.useAgentStore.getState().interviewDrafts, {});
  assert.equal(posts, 0);
  next.unmount();
});

function editorRuntime(s, props) {
  const view = s.LessonContentEditor(props);
  const runtime = s.renderer(view.type);
  let tree;
  const render = () => { tree = runtime.render(props); s.mountEffects(); return tree; };
  const choose = (index = 1) => {
    nodes(tree).find((node) => node.props?.["aria-label"]?.startsWith(`Редактировать блок ${index}:`)).props.onClick();
    render();
    nodes(tree).find((node) => node.type === "button" && node.props?.children === "ИИ-редактор").props.onClick();
    return render();
  };
  render(); render();
  return { runtime, render, choose };
}
const editorInput = (tree) => nodes(tree).find((node) => node.type === "textarea" && node.props.maxLength === 10000);
const editorSend = (tree) => nodes(tree).find((node) => node.props?.className === "lesson-ai-send");

test("editor block inputs/history survive reload with id-less API blocks; no restored proposal apply/POST", async () => {
  const s = await stores({ views: true });
  s.session.setState({ user: { id: "user" } });
  let posts = 0;
  let applied = 0;
  s.api.askEditorAgent = async () => { posts++; return { chatId: "editor-server", parsedContent: { md_content: "AI suggestion" } }; };
  const props = { courseId: "course", lesson: { id: "lesson", content_blocks: [
    { content_type: "text", md_content: "first" }, { content_type: "text", md_content: "second" },
  ] }, onChange: () => applied++ };
  const editor = editorRuntime(s, props);
  let tree = editor.choose();
  editorInput(tree).props.onChange({ target: { value: "change first" } });
  tree = editor.render();
  await editorSend(tree).props.onClick();
  tree = editor.render();
  assert.equal(posts, 1);
  assert.ok(nodes(tree).some((node) => node.props?.children === "Применить"));
  const staleApply = nodes(tree).find((node) => node.props?.children === "Применить");
  const firstKey = Object.keys(s.useAgentStore.getState().conversations)[0];
  // Keep an unsent draft even while a proposal is visible (store action is the same input path).
  s.useAgentStore.getState().setInterviewDraft(firstKey, "first unsent");
  tree = editor.choose(2);
  assert.equal(editorInput(tree).props.value, "");
  editorInput(tree).props.onChange({ target: { value: "second unsent" } });
  staleApply.props.onClick();
  assert.equal(applied, 0);
  tree = editor.render();
  const staleInput = editorInput(tree);
  const setItem = s.storage.setItem;
  s.storage.setItem = () => { throw Error("quota"); };
  staleInput.props.onChange({ target: { value: "second quota draft" } });
  assert.equal(warningIn(s, editor.render()).props.role, "alert");
  s.storage.setItem = setItem;
  editorInput(editor.render()).props.onChange({ target: { value: "second unsent" } });
  editor.runtime.unmount();
  staleInput.props.onChange({ target: { value: "unmounted draft" } });
  const reloaded = await stores({ views: true, storage: s.storage, api: s.api });
  reloaded.session.setState({ user: { id: "user" } });
  const next = editorRuntime(reloaded, props);
  tree = next.choose();
  assert.equal(editorInput(tree).props.value, "first unsent");
  assert.ok(JSON.stringify(tree).includes("Правка готова"));
  assert.equal(nodes(tree).some((node) => node.props?.children === "Применить"), false);
  tree = next.choose(2);
  assert.equal(editorInput(tree).props.value, "second unsent");
  assert.equal(posts, 1);
  assert.equal(applied, 0);
  reloaded.session.setState({ organizationId: "other", sessionContext: 2 });
  editorInput(tree).props.onChange({ target: { value: "foreign" } });
  await editorSend(tree).props.onClick();
  assert.equal(posts, 1);
  assert.equal(applied, 0);
  assert.deepEqual(reloaded.useAgentStore.getState().interviewDrafts, {});
  next.runtime.unmount();
});

test("editor rejects stale work before image POST and after AI response, including automatic image apply", async () => {
  const s = await stores({ views: true });
  s.session.setState({ user: { id: "user" } });
  let posts = 0;
  let applies = 0;
  let resolveRead;
  let resolveAi;
  const originalFetch = globalThis.fetch;
  const props = { courseId: "course", lesson: { id: "images", content_blocks: [
    { id: "image", content_type: "image", image_id: "old-image" },
    { id: "text", content_type: "text", md_content: "another block" },
  ] }, onChange: () => applies++ };
  const editor = editorRuntime(s, props);
  try {
    globalThis.fetch = () => new Promise((resolve) => { resolveRead = resolve; });
    s.api.askEditorAgent = () => { posts++; return new Promise((resolve) => { resolveAi = resolve; }); };
    let tree = editor.choose();
    editorInput(tree).props.onChange({ target: { value: "update image" } });
    const beforePost = editorSend(editor.render()).props.onClick();
    editor.choose(2);
    resolveRead({ ok: true, arrayBuffer: async () => new ArrayBuffer(1) });
    await beforePost;
    assert.equal(posts, 0, "leaving block during image read must prevent POST");
    globalThis.fetch = async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(1) });
    tree = editor.choose();
    editorInput(tree).props.onChange({ target: { value: "try image again" } });
    const pending = editorSend(editor.render()).props.onClick();
    await new Promise(setImmediate);
    assert.equal(posts, 1);
    editor.choose(2);
    resolveAi({ chatId: "image-chat", parsedContent: { image_id: "new-image" } });
    await pending;
    assert.equal(applies, 0, "late image response must not auto-apply");
    tree = editor.render();
    assert.equal(nodes(tree).some((node) => node.props?.children === "Применить"), false);
    editor.runtime.unmount();
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("same-version agent rehydrate whitelists malformed valid JSON before chat/draft rendering", async () => {
  const storage = memory();
  const scoped = createScopedStorage(() => storage, () => reloadScope(context));
  const base = { agent: "mentor", courseId: "course", chatId: "server-chat", status: "success", activeRequestId: 123, error: { bad: true }, proposal: { apply: true } };
  scoped.setItem("course-generation:active-course", "course");
  scoped.setItem("ai-course-agent-chats-v1", JSON.stringify({ version: 2, state: {
    conversations: {
      "mentor:course:lesson": { ...base, messages: "not an array" },
      "editor:course:lesson:block": { ...base, agent: "editor", messages: {} },
      "interviewer:course:": { ...base, agent: "interviewer", messages: null, chatId: {} },
      mixed: { ...base, messages: [null, false, [], "message", {},
        { id: "object-text", role: "assistant", text: {} },
        { id: "system", role: "system", text: "not a chat role" },
        { id: 12, role: "user", text: "invalid id" },
        { id: " ", role: "user", text: "empty id" },
        { id: "u", role: "user", text: "question", file: { bytes: "discard" } },
        { id: "a", role: "assistant", text: "answer", parsedContent: { md_content: "do not apply" } },
      ] },
      badAgent: { ...base, agent: "unknown", messages: [] },
      badCourse: { ...base, courseId: {}, messages: [] },
      emptyCourse: { ...base, courseId: " ", messages: [] },
      array: [], scalar: "chat", nil: null,
    },
    creatorDrafts: {
      "interviewer:course:": { stepIndex: "3", answers: "string answers", inputValue: {}, files: {}, unknown: true },
      good: { stepIndex: 99, inputValue: "unsent", answers: { title: "Course", goal: {}, duration: [], format: "practice", unknown: "discard" },
        files: [null, [], "file", {}, { id: {}, name: "bad" },
          { id: "file", name: "notes.txt", sizeKb: "wrong", size: 42, lastModified: {}, file: { bytes: "never restore" }, unknown: true }],
        extra: "discard",
      },
      negative: { stepIndex: -1, answers: [], files: null },
      fractional: { stepIndex: 2.5 },
      scalar: "draft", array: [], nil: null,
    },
    interviewDrafts: { good: "keep input", object: {}, array: [], number: 123, nil: null },
    generations: {
      mixed: { hasStarted: "true", isGenerating: {}, taskId: [], generatedCourseId: {}, status: {}, courseStatus: [], progress: "90", error: {}, startedAt: "invalid", extra: true },
      "interviewer:course:": "invalid generation",
      orphan: { hasStarted: true, isGenerating: true, generatedCourseId: "other-course" },
    },
    sendMessage: "poison method", unknownRoot: true,
  } }));
  let posts = 0;
  const api = { askEditorAgent: () => posts++, askMentorAgent: () => posts++, askInterviewerAgent: () => posts++ };
  const s = await stores({ views: true, storage, api });
  const state = s.useAgentStore.getState();
  assert.equal(typeof state.sendMessage, "function");
  assert.equal("unknownRoot" in state, false);
  assert.deepEqual(Object.keys(state.conversations).sort(), ["mentor:course:lesson", "editor:course:lesson:block", "interviewer:course:", "mixed"].sort());
  for (const key of ["mentor:course:lesson", "editor:course:lesson:block", "interviewer:course:"]) {
    assert.deepEqual(state.conversations[key].messages, []);
    assert.equal(state.conversations[key].status, "idle");
    assert.equal(state.conversations[key].error, "");
    assert.equal(state.conversations[key].activeRequestId, null);
    assert.equal("proposal" in state.conversations[key], false);
  }
  assert.equal(state.conversations["interviewer:course:"].chatId, null);
  assert.equal(state.conversations.mixed.chatId, "server-chat");
  assert.deepEqual(state.conversations.mixed.messages, [
    { id: "u", role: "user", text: "question" }, { id: "a", role: "assistant", text: "answer" },
  ]);
  assert.deepEqual(state.creatorDrafts["interviewer:course:"], { stepIndex: 0, answers: {}, inputValue: "", files: [] });
  assert.deepEqual(state.creatorDrafts.good, {
    stepIndex: 7, inputValue: "unsent", answers: { title: "Course", format: "practice" },
    files: [{ id: "file", name: "notes.txt", sizeKb: 0, size: 42, lastModified: null }],
  });
  assert.equal(state.creatorDrafts.negative.stepIndex, 0);
  assert.equal(state.creatorDrafts.fractional.stepIndex, 0);
  assert.equal(state.creatorDrafts.scalar, undefined);
  assert.equal(state.creatorDrafts.array, undefined);
  assert.deepEqual(state.interviewDrafts, { good: "keep input" });
  assert.deepEqual(state.generations, { mixed: {
    hasStarted: false, isGenerating: false, taskId: null, generatedCourseId: null,
    status: "Жду ответы в чате", courseStatus: "", progress: 0, error: "", startedAt: null,
  } });
  const mentorView = s.LessonAiChat({ courseId: "course", lessonId: "lesson", isOpen: true });
  assert.doesNotThrow(() => mentorView.type(mentorView.props));
  const creatorView = s.CreatorChatView();
  assert.doesNotThrow(() => creatorView.type(creatorView.props));
  assert.equal(posts, 0);
  // Persisting again must not bring back unknown fields or nested file payloads.
  state.setInterviewDraft("good", "still safe");
  const written = JSON.parse(scoped.getItem("ai-course-agent-chats-v1")).state;
  assert.deepEqual(written.creatorDrafts.good, state.creatorDrafts.good);
  assert.equal(JSON.stringify(written).includes("never restore"), false);
});

test("same-version stores reject malformed root/maps and prototype keys without overwriting actions", async () => {
  const s = await stores();
  const agent = s.useAgentStore;
  const jobs = s.useGenerationJobsStore;
  for (const bad of [null, false, 123, "string", [], [{ agent: "mentor", courseId: "course" }]]) {
    for (const state of [bad, { conversations: bad, creatorDrafts: bad, interviewDrafts: bad, generations: bad }]) {
      s.scopedReloadStorage.setItem("ai-course-agent-chats-v1", JSON.stringify({ version: 2, state }));
      agent.persist.rehydrate();
      assert.deepEqual(agent.getState().conversations, {});
      assert.deepEqual(agent.getState().creatorDrafts, {});
      assert.deepEqual(agent.getState().interviewDrafts, {});
      assert.deepEqual(agent.getState().generations, {});
      assert.equal(typeof agent.getState().sendMessage, "function");
    }
    for (const state of [bad, { jobs: bad, startJob: "poison" }]) {
      s.scopedReloadStorage.setItem("ai-course-generation-jobs-v1", JSON.stringify({ version: 1, state }));
      jobs.persist.rehydrate();
      assert.deepEqual(jobs.getState().jobs, {});
      assert.equal(typeof jobs.getState().startJob, "function");
    }
  }
  const poisoned = JSON.parse('{"__proto__":{"agent":"mentor","courseId":"course","messages":[]},"constructor":{"agent":"mentor","courseId":"course","messages":[]}}');
  s.scopedReloadStorage.setItem("ai-course-agent-chats-v1", JSON.stringify({ version: 2, state: { conversations: poisoned, creatorDrafts: poisoned, interviewDrafts: { constructor: "poison" } } }));
  agent.persist.rehydrate();
  assert.deepEqual(agent.getState().conversations, {});
  assert.deepEqual(agent.getState().creatorDrafts, {});
  assert.deepEqual(agent.getState().interviewDrafts, {});
});

test("same-version generation jobs whitelist safe polling state and discard malformed jobs", async () => {
  const storage = memory();
  const scoped = createScopedStorage(() => storage, () => reloadScope(context));
  const base = { kind: "module", courseId: "course", status: "running", startedAt: "2026-11-01T00:00:00.000Z", knownIds: ["known"], resultId: "module" };
  const job = (key, patch = {}) => ({ ...base, key, ...patch });
  scoped.setItem("ai-course-generation-jobs-v1", JSON.stringify({ version: 1, state: {
    jobs: {
      valid: job("valid", { taskId: "task", chatKey: "chat", order: 2, resultTitle: "Module", lessonsCount: 3, lastChangeAt: "2026-11-01T00:00:00.000Z", extra: { apply: true } }),
      defaults: job("defaults", { status: "done", taskId: {}, chatKey: [], order: "2", resultTitle: {}, lessonsCount: -1, lastChangeAt: {}, error: {} }),
      badKind: job("badKind", { kind: "unknown" }),
      badCourse: job("badCourse", { courseId: {} }),
      missingModule: job("missingModule", { kind: "lesson" }),
      badModule: job("badModule", { kind: "lesson", moduleId: [] }),
      badKnown: job("badKnown", { knownIds: {} }),
      badKnownEntry: job("badKnownEntry", { knownIds: ["known", {}] }),
      badTime: job("badTime", { startedAt: "not a date" }),
      badStatus: job("badStatus", { status: {} }),
      mismatch: job("other-key"), nil: null, string: "job", array: [],
    },
    updateJob: "poison", unknownRoot: true,
  } }));
  const s = await stores({ views: true, storage });
  const state = s.useGenerationJobsStore.getState();
  assert.deepEqual(Object.keys(state.jobs), ["valid", "defaults"]);
  assert.equal(typeof state.updateJob, "function");
  assert.equal("unknownRoot" in state, false);
  assert.deepEqual(state.jobs.valid, {
    key: "valid", kind: "module", courseId: "course", moduleId: "", order: 2,
    taskId: "task", chatKey: "chat", knownIds: ["known"], startedAt: base.startedAt,
    status: "running", resultId: "module", resultTitle: "Module", lessonsCount: 3,
    lastChangeAt: base.startedAt, error: "",
  });
  assert.equal(state.jobs.defaults.taskId, null);
  assert.equal(state.jobs.defaults.order, null);
  assert.equal(state.jobs.defaults.lessonsCount, 0);
  assert.equal(state.jobs.defaults.resultTitle, "");
  let gets = 0;
  let posts = 0;
  s.api.getModuleBasicInfo = () => { gets++; return new Promise(() => {}); };
  s.api.askModuleInterviewerAgent = () => posts++;
  s.useGenerationJobsWatcher({});
  const unmount = s.mountEffects();
  assert.equal(gets, 1, "only the valid running job may poll");
  assert.equal(posts, 0);
  unmount();
  state.updateJob("valid", { extra: "must not persist" });
  const written = JSON.parse(scoped.getItem("ai-course-generation-jobs-v1")).state;
  assert.deepEqual(written.jobs.valid, state.jobs.valid);
});
