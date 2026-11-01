import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const require = createRequire(import.meta.url);
const { outputFiles } = await build({
  stdin: {
    contents: `
      export * from "./src/stores/themeStore.js";
      export * from "./src/stores/uiLayoutStore.js";
      export * from "./src/utils/storage.js";
    `,
    resolveDir: fileURLToPath(new URL("../../", import.meta.url)),
  },
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  packages: "external",
});

const THEME_KEY = "app-theme-storage";
const UI_KEY = "app-ui-layout-storage";
let originalGlobals;
beforeEach(() => {
  originalGlobals = ["window", "localStorage"].map((name) => [
    name,
    Object.getOwnPropertyDescriptor(globalThis, name),
  ]);
});
afterEach(() => {
  for (const [name, descriptor] of originalGlobals) {
    if (descriptor) Object.defineProperty(globalThis, name, descriptor);
    else delete globalThis[name];
  }
});

function setGlobal(name, value) {
  Object.defineProperty(globalThis, name, {
    configurable: true,
    writable: true,
    value,
  });
}

function setup({
  mode,
  theme,
  layout,
  themeVersion = 1,
  uiVersion = 2,
  darkSystem = false,
} = {}) {
  const data = new Map();
  if (theme !== undefined)
    data.set(
      THEME_KEY,
      JSON.stringify({ state: theme, version: themeVersion }),
    );
  if (layout !== undefined)
    data.set(UI_KEY, JSON.stringify({ state: layout, version: uiVersion }));
  if (mode === "corrupt") {
    data.set(THEME_KEY, "{broken");
    data.set(UI_KEY, "{broken");
  }
  const failures = new Set([mode]);
  const writes = [];
  const storage = {
    getItem(key) {
      if (failures.has("getItem")) throw new Error("read denied");
      return data.get(key) ?? null;
    },
    setItem(key, value) {
      writes.push(key);
      if (failures.has("setItem"))
        throw new DOMException("quota exceeded", "QuotaExceededError");
      data.set(key, value);
    },
    removeItem(key) {
      if (failures.has("removeItem")) throw new Error("remove denied");
      data.delete(key);
    },
  };
  if (mode === "noWindow") {
    delete globalThis.window;
    delete globalThis.localStorage;
  } else {
    const window = { matchMedia: () => ({ matches: darkSystem }) };
    if (mode === "blockedGetter") {
      Object.defineProperty(window, "localStorage", {
        get() {
          throw new DOMException("access denied", "SecurityError");
        },
      });
      delete globalThis.localStorage;
    } else {
      window.localStorage = storage;
      setGlobal("localStorage", storage);
    }
    setGlobal("window", window);
  }
  // Evaluate the real stores with real Zustand; only browser storage is replaced.
  const module = { exports: {} };
  new Function("require", "module", "exports", outputFiles[0].text)(
    require,
    module,
    module.exports,
  );
  return {
    ...module.exports,
    theme: module.exports.useThemeStore,
    ui: module.exports.useUiLayoutStore,
    data,
    storage,
    failures,
    writes,
  };
}

function assertHydrated(theme, ui) {
  assert.equal(theme.getState().hasHydrated, true);
  assert.equal(ui.getState().hasHydrated, true);
  assert.equal(theme.persist.hasHydrated(), true);
  assert.equal(ui.persist.hasHydrated(), true);
}

function exerciseRouteAndThemeActions(theme, ui) {
  theme.getState().setTheme("dark");
  theme.getState().toggleTheme();
  assert.equal(theme.getState().theme, "light");
  ui.getState().setActiveProfileTab("courses");
  ui.getState().setCoursesPage(3);
  ui.getState().recordRoute("/courses");
  ui.getState().recordRoute("/courses/lesson");
  ui.getState().saveScrollPosition("/courses", 123.6);
  ui.getState().setLessonActiveTab("lesson", "practice");
  assert.equal(ui.getState().getPreviousRoute("/courses/lesson"), "/courses");
  assert.equal(ui.getState().getScrollPosition("/courses"), 124);
  assert.equal(ui.getState().getLessonActiveTab("lesson"), "practice");
  assert.equal(ui.getState().coursesPage, 3);
}

for (const mode of [
  "noWindow",
  "blockedGetter",
  "getItem",
  "setItem",
  "removeItem",
  "corrupt",
]) {
  test(`actual UI/theme stores hydrate and route actions survive ${mode}`, async () => {
    const { theme, ui, failures, writes } = setup({ mode });
    assertHydrated(theme, ui);
    assert.doesNotThrow(() => exerciseRouteAndThemeActions(theme, ui));
    assert.doesNotThrow(() => theme.persist.clearStorage());
    assert.doesNotThrow(() => ui.persist.clearStorage());
    failures.clear();
    await theme.persist.rehydrate();
    await ui.persist.rehydrate();
    assertHydrated(theme, ui);
    assert.equal(ui.getState().coursesPage, 3);
    assert.equal(ui.getState().getScrollPosition("/courses"), 124);
    assert.equal(ui.getState().getLessonActiveTab("lesson"), "practice");
    assert.ok(writes.every((key) => key === THEME_KEY || key === UI_KEY));
  });
}

test("quota appearing after hydration does not escape route/theme effects or lose live state", () => {
  const { theme, ui, failures } = setup();
  assertHydrated(theme, ui);
  failures.add("setItem");
  assert.doesNotThrow(() => exerciseRouteAndThemeActions(theme, ui));
  assert.equal(ui.getState().activeProfileTab, "courses");
  assert.equal(ui.getState().coursesPage, 3);
  failures.delete("setItem");
  ui.getState().setCoursesPage(4);
  theme.getState().setTheme("dark");
});

for (const invalidState of [
  null,
  [],
  "broken",
  42,
  true,
  {
    theme: { bad: "dark" },
    hasHydrated: false,
    setHasHydrated: null,
    setTheme: null,
    toggleTheme: "not a function",
  },
]) {
  test(`same-version theme merge rejects malformed state ${JSON.stringify(invalidState)}`, () => {
    const { theme, ui } = setup({ theme: invalidState });
    assertHydrated(theme, ui);
    assert.equal(theme.getState().theme, "light");
    assert.doesNotThrow(() => theme.getState().toggleTheme());
    assert.equal(theme.getState().theme, "dark");
  });
}

for (const value of [
  null,
  [],
  "bad",
  7,
  true,
  {
    activeProfileTab: {},
    coursesPage: { valueOf: null, toString: null },
    scrollPositions: null,
    activeLessonTabs: null,
    routeHistory: {},
    hasHydrated: false,
    setHasHydrated: null,
    recordRoute: null,
    getScrollPosition: null,
    getLessonActiveTab: null,
  },
]) {
  test(`same-version UI merge rejects malformed state ${JSON.stringify(value)}`, () => {
    const { theme, ui } = setup({ layout: value });
    assertHydrated(theme, ui);
    assert.equal(ui.getState().activeProfileTab, "overview");
    assert.equal(ui.getState().coursesPage, 1);
    assert.deepEqual(ui.getState().scrollPositions, {});
    assert.deepEqual(ui.getState().activeLessonTabs, {});
    assert.deepEqual(ui.getState().routeHistory, []);
    assert.doesNotThrow(() => exerciseRouteAndThemeActions(theme, ui));
  });
}

test("same-version merge whitelists validated UI fields and never restores route history/actions", () => {
  const { theme, ui } = setup({
    theme: { theme: "system", setTheme: null, extra: "discard" },
    layout: {
      activeProfileTab: "courses",
      coursesPage: "2.6",
      scrollPositions: { "/ok": 12.5, "/negative": -5, "/bad": "20", "": 30 },
      activeLessonTabs: { lesson: "questions", bad: "unknown", "": "practice" },
      routeHistory: ["/untrusted"],
      recordRoute: null,
      extra: "discard",
    },
  });
  assertHydrated(theme, ui);
  assert.equal(theme.getState().theme, "system");
  assert.equal(ui.getState().activeProfileTab, "courses");
  assert.equal(ui.getState().coursesPage, 3);
  assert.deepEqual(ui.getState().scrollPositions, {
    "/ok": 13,
    "/negative": 0,
  });
  assert.deepEqual(ui.getState().activeLessonTabs, { lesson: "questions" });
  assert.deepEqual(ui.getState().routeHistory, []);
  assert.equal(theme.getState().extra, undefined);
  assert.equal(ui.getState().extra, undefined);
  assert.doesNotThrow(() => exerciseRouteAndThemeActions(theme, ui));
});

test("malformed nested maps are not interpreted as records", () => {
  for (const badMap of [null, [], [10, 20], "bad", 12]) {
    const { ui } = setup({
      layout: { scrollPositions: badMap, activeLessonTabs: badMap },
    });
    assert.equal(ui.getState().hasHydrated, true);
    assert.deepEqual(ui.getState().scrollPositions, {});
    assert.deepEqual(ui.getState().activeLessonTabs, {});
    assert.doesNotThrow(() => ui.getState().recordRoute("/courses"));
  }
});

test("UI cache maps remain bounded to 50 entries", () => {
  const { ui } = setup({
    layout: {
      scrollPositions: Object.fromEntries(
        Array.from({ length: 60 }, (_, i) => [`/${i}`, i]),
      ),
      activeLessonTabs: Object.fromEntries(
        Array.from({ length: 60 }, (_, i) => [`lesson-${i}`, "theory"]),
      ),
    },
  });
  assert.equal(Object.keys(ui.getState().scrollPositions).length, 50);
  assert.equal(Object.keys(ui.getState().activeLessonTabs).length, 50);
  assert.equal(ui.getState().getScrollPosition("/0"), undefined);
  assert.equal(ui.getState().getScrollPosition("/59"), 59);
});

test("theme defaults, system resolution, supported values and version reset are unchanged", () => {
  for (const themeValue of ["light", "dark", "system"]) {
    const { theme, resolveTheme } = setup({
      theme: { theme: themeValue },
      darkSystem: true,
    });
    assert.equal(theme.getState().theme, themeValue);
    assert.equal(resolveTheme("system"), "dark");
    theme.getState().setTheme("invalid");
    assert.equal(theme.getState().theme, themeValue);
    theme.getState().toggleTheme();
    assert.equal(
      theme.getState().theme,
      themeValue === "light" ? "dark" : "light",
    );
  }
  for (const themeVersion of [0, 2]) {
    const { theme, data } = setup({ theme: { theme: "dark" }, themeVersion });
    assert.equal(theme.getState().theme, "light");
    assert.equal(JSON.parse(data.get(THEME_KEY)).version, 1);
  }
});

test("legacy UI migration preserves supported fields, resets history and keeps version 2", () => {
  const { ui, data } = setup({
    uiVersion: 1,
    layout: {
      activeProfileTab: "courses",
      coursesPage: 2,
      scrollPositions: { "/courses": 42 },
      activeLessonTabs: { lesson: "practice" },
      routeHistory: ["/old"],
      recordRoute: null,
    },
  });
  assert.equal(ui.getState().activeProfileTab, "courses");
  assert.equal(ui.getState().coursesPage, 2);
  assert.equal(ui.getState().getScrollPosition("/courses"), 42);
  assert.equal(ui.getState().getLessonActiveTab("lesson"), "practice");
  assert.deepEqual(ui.getState().routeHistory, []);
  assert.equal(JSON.parse(data.get(UI_KEY)).version, 2);
});

test("only existing keys and persisted field sets are written", () => {
  const { theme, ui, data, writes } = setup();
  exerciseRouteAndThemeActions(theme, ui);
  assert.deepEqual([...new Set(writes)].sort(), [THEME_KEY, UI_KEY].sort());
  assert.deepEqual(Object.keys(JSON.parse(data.get(THEME_KEY)).state), [
    "theme",
  ]);
  assert.deepEqual(
    Object.keys(JSON.parse(data.get(UI_KEY)).state).sort(),
    [
      "activeProfileTab",
      "coursesPage",
      "scrollPositions",
      "activeLessonTabs",
    ].sort(),
  );
});
