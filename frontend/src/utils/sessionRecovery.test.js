import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const frontendDirectory = fileURLToPath(new URL("../../", import.meta.url));
const require = createRequire(import.meta.url);
const { outputFiles } = await build({
  stdin: {
    contents: `
      export * from "./src/utils/api.js";
      export * from "./src/stores/sessionStore.js";
      export * from "./src/stores/permissionStore.js";
    `,
    resolveDir: frontendDirectory,
  },
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  packages: "external",
  define: { "import.meta.env": "{}" },
  plugins: [{
    name: "unrelated-diagram-validation",
    setup(builder) {
      // Only diagram rendering is stubbed; API, storage and both stores are real.
      builder.onResolve({ filter: /MermaidDiagram\.jsx$/ }, () => ({
        path: "diagram",
        namespace: "test-stub",
      }));
      builder.onLoad({ filter: /.*/, namespace: "test-stub" }, () => ({
        contents: "export const validateMermaidSource = async value => value;",
      }));
    },
  }],
});

const globalNames = ["window", "localStorage", "fetch"];
let originalGlobals;
beforeEach(() => {
  originalGlobals = new Map(globalNames.map((name) => [
    name, Object.getOwnPropertyDescriptor(globalThis, name),
  ]));
});
afterEach(() => {
  for (const [name, descriptor] of originalGlobals) {
    if (descriptor) Object.defineProperty(globalThis, name, descriptor);
    else delete globalThis[name];
  }
});

function setGlobal(name, value) {
  Object.defineProperty(globalThis, name, {
    configurable: true, writable: true, value,
  });
}

function memoryStorage(entries = []) {
  const data = new Map(entries);
  const failures = new Set();
  const access = (method, operation) => (...args) => {
    if (failures.has(method)) throw new Error(`storage ${method} blocked`);
    return operation(...args);
  };
  return {
    data,
    failures,
    getItem: access("getItem", (key) => data.get(key) ?? null),
    setItem: access("setItem", (key, value) => data.set(key, String(value))),
    removeItem: access("removeItem", (key) => data.delete(key)),
  };
}

function setup({ storage = memoryStorage(), blockedGetter = false, noWindow = false } = {}) {
  if (noWindow) {
    delete globalThis.window;
    delete globalThis.localStorage;
  } else {
    const window = {};
    if (blockedGetter) {
      Object.defineProperty(window, "localStorage", {
        get() { throw new Error("storage getter blocked"); },
      });
      delete globalThis.localStorage;
    } else {
      window.localStorage = storage;
      setGlobal("localStorage", storage);
    }
    setGlobal("window", window);
  }
  setGlobal("fetch", async (url) => {
    throw new Error(`Unexpected fetch: ${url}`);
  });

  // Re-evaluate the actual bundle so each test gets isolated module singleflights.
  const module = { exports: {} };
  new Function("require", "module", "exports", outputFiles[0].text)(
    require, module, module.exports,
  );
  const api = module.exports;
  const session = api.useSessionStore;
  const permissions = api.usePermissionStore;
  return {
    api, session, permissions, storage,
    start(id = "a", expiresAt = Date.now() / 1000 + 3600) {
      session.getState().setTokens({
        access_token: id, refresh_token: `r-${id}`, expires_at: expiresAt,
      }, { membershipId: `m-${id}`, organizationId: `o-${id}` });
    },
  };
}

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status, headers: { "content-type": "application/json" },
  });
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

const isStale = (error) => error.code === "STALE_SESSION";

test("transient refresh network/503/429 and malformed success retain credentials", async () => {
  for (const failure of ["offline", 503, 429, "malformed"]) {
    const { api, start } = setup();
    start("a", 1);
    globalThis.fetch = async () => {
      if (failure === "offline") throw new TypeError("offline");
      return json({}, failure === "malformed" ? 200 : failure);
    };
    await assert.rejects(api.apiFetch("/test"), (error) =>
      failure === "offline" ? error.message === "offline" :
        error.status === (failure === "malformed" ? 502 : failure));
    assert.equal(api.readStoredSession().accessToken, "a");
  }
});

test("refresh-only reload and StrictMode-style parallel loads are singleflight", async () => {
  const storage = memoryStorage([["aicolab_session", JSON.stringify({
    refreshToken: "r", membershipId: "m",
  })]]);
  const { api, session, permissions } = setup({ storage });
  const gate = deferred();
  const calls = { refresh: 0, identity: 0, user: 0 };
  globalThis.fetch = async (url) => {
    if (url.endsWith("/refresh")) {
      calls.refresh++;
      await gate.promise;
      return json({ access_token: "new", expires_at: Date.now() / 1000 + 3600 });
    }
    if (url.endsWith("/identity")) {
      calls.identity++;
      return json({ membership_id: "m", organization_id: "o", permissions: ["course:read"] });
    }
    calls.user++;
    return json({ id: "u" });
  };
  const jobs = [
    session.getState().loadIdentity(), session.getState().loadIdentity(),
    session.getState().loadCurrentUser(), session.getState().loadCurrentUser(),
    permissions.getState().loadPermissions(), permissions.getState().loadPermissions(),
  ];
  gate.resolve();
  await Promise.all(jobs);
  assert.deepEqual(calls, { refresh: 1, identity: 1, user: 1 });
  assert.equal(permissions.getState().hasPermission("course:read"), true);
  assert.equal(api.readStoredSession().organizationId, "o");
  assert.equal(JSON.parse(storage.getItem("aicolab_session")).organizationId, "o");
});

test("a late 401 uses the rotated access token without a second refresh", async () => {
  const { api, start } = setup();
  start();
  const gate = deferred();
  let refreshes = 0;
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/refresh")) {
      refreshes++;
      return json({ access_token: "new", expires_at: Date.now() / 1000 + 3600 });
    }
    if (options.headers.get("Authorization") === "Bearer a") {
      if (url.endsWith("/late")) await gate.promise;
      return json({}, 401);
    }
    assert.equal(options.headers.get("Authorization"), "Bearer new");
    return json({});
  };
  const early = api.apiFetch("/early");
  const late = api.apiFetch("/late");
  await early;
  gate.resolve();
  assert.equal((await late).status, 200);
  assert.equal(refreshes, 1);
});

for (const status of [200, 401, 503]) {
  test(`obsolete refresh (${status}) cannot replace or clear a newer session`, async () => {
    const { api, start } = setup();
    start("a", 1);
    const gate = deferred();
    globalThis.fetch = () => gate.promise;
    const checked = assert.rejects(api.apiFetch("/test"), isStale);
    start("b");
    gate.resolve(json({ access_token: "obsolete" }, status));
    await checked;
    assert.equal(api.readStoredSession().accessToken, "b");
  });

  test(`obsolete identity/profile (${status}) cannot update session or permissions`, async () => {
    const { session, permissions, start } = setup();
    start();
    const identityGate = deferred();
    const userGate = deferred();
    globalThis.fetch = (url) => url.endsWith("/identity") ? identityGate.promise : userGate.promise;
    const oldIdentity = session.getState().loadIdentity()
      .then((identity) => permissions.getState().setPermissionsFromIdentity(identity));
    const oldUser = session.getState().loadCurrentUser();
    start("b");
    globalThis.fetch = async (url) => json(url.endsWith("/identity") ?
      { membership_id: "m-b", permissions: ["course:update"] } : { id: "b" });
    await Promise.all([session.getState().loadIdentity(), session.getState().loadCurrentUser()]);
    identityGate.resolve(json({ membership_id: "m-a", permissions: ["course:delete"] }, status));
    userGate.resolve(json({ id: "a" }, status));
    await Promise.all([oldIdentity, oldUser]);
    assert.equal(session.getState().user.id, "b");
    assert.equal(session.getState().membershipId, "m-b");
    assert.equal(permissions.getState().hasPermission("course:update"), true);
    assert.equal(permissions.getState().hasPermission("course:delete"), false);
  });
}

test("permissions errors remain retryable and null App callbacks never mark ready", async () => {
  const { api, permissions, start } = setup();
  start();
  globalThis.fetch = async () => { throw new TypeError("offline"); };
  await permissions.getState().loadPermissions();
  permissions.getState().setPermissionsFromIdentity(null);
  assert.equal(permissions.getState().isLoaded, false);
  assert.match(permissions.getState().error, /offline/);
  assert.equal(api.readStoredSession().accessToken, "a");
  globalThis.fetch = async () => json({ permissions: [] });
  await permissions.getState().loadPermissions();
  assert.equal(permissions.getState().isLoaded, true);
  assert.deepEqual(permissions.getState().permissions, []);
});

test("permission retry failure is not reset by unrelated session updates", async () => {
  const { session, permissions, start } = setup();
  start();
  globalThis.fetch = async () => json({ permissions: ["course:read"] });
  await permissions.getState().loadPermissions();
  assert.equal(permissions.getState().hasPermission("course:read"), true);
  globalThis.fetch = async () => { throw new TypeError("offline"); };
  await permissions.getState().loadPermissions();
  session.setState({ user: { id: "u" } });
  assert.equal(permissions.getState().isLoaded, false);
  assert.equal(permissions.getState().hasPermission("course:read"), false);
  globalThis.fetch = async () => json({ permissions: ["course:update"] });
  await Promise.all([permissions.getState().loadPermissions(), permissions.getState().loadPermissions()]);
  permissions.getState().setPermissionsFromIdentity(session.getState().identity);
  permissions.getState().setPermissionsFromIdentity(null);
  assert.equal(permissions.getState().hasPermission("course:update"), true);
  assert.equal(permissions.getState().hasPermission("course:read"), false);
});

test("old identity/profile finally cannot erase a new context's singleflight", async () => {
  for (const method of ["loadIdentity", "loadCurrentUser"]) {
    const { session, start } = setup();
    start();
    const oldGate = deferred();
    const newGate = deferred();
    let calls = 0;
    globalThis.fetch = () => ++calls === 1 ? oldGate.promise : newGate.promise;
    const old = session.getState()[method]();
    start("b");
    const current = session.getState()[method]();
    oldGate.resolve(json({}));
    await old;
    const duplicate = session.getState()[method]();
    assert.equal(calls, 2);
    newGate.resolve(json({ id: "b", membership_id: "m-b" }));
    await Promise.all([current, duplicate]);
  }
});

test("logout is immediate; delayed remote logout cannot clear a newer login", async () => {
  const { api, session, start } = setup();
  start();
  const gate = deferred();
  globalThis.fetch = () => gate.promise;
  const logout = session.getState().logout();
  assert.equal(api.readStoredSession().accessToken, null);
  start("b");
  gate.resolve(json({}));
  await logout;
  assert.equal(api.readStoredSession().accessToken, "b");
});

test("authoritative refresh rejection respects clearOnUnauthorized", async () => {
  for (const clearOnUnauthorized of [true, false]) {
    const { api, start } = setup();
    start("a", 1);
    globalThis.fetch = async () => json({}, 401);
    await assert.rejects(api.apiFetch("/test", {}, { clearOnUnauthorized }),
      (error) => error.code === "SESSION_EXPIRED");
    assert.equal(api.readStoredSession().accessToken, clearOnUnauthorized ? null : "a");
  }
});

test("logout invalidates an outstanding login response", async () => {
  const { session } = setup();
  const gate = deferred();
  globalThis.fetch = () => gate.promise;
  const checked = assert.rejects(session.getState().loginWithCredentials({
    email: "test@example.com", password: "test",
  }), isStale);
  session.getState().clearSession();
  gate.resolve(json({ authentication_token: "obsolete", memberships: [{ id: "old" }] }));
  await checked;
  assert.equal(session.getState().authenticationToken, null);
  assert.equal(session.getState().isLoading, false);
});

test("out-of-order membership selection cannot replace a newer selection", async () => {
  const { api, session } = setup();
  session.setState({ authenticationToken: "auth", memberships: [{ id: "a" }, { id: "b" }] });
  const gate = deferred();
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/auth/token")) {
      if (JSON.parse(options.body).membership_id === "a") return gate.promise;
      return json({ access_token: "b", refresh_token: "r-b", expires_at: Date.now() / 1000 + 3600 });
    }
    return json(url.endsWith("/identity") ? { membership_id: "b", permissions: [] } : { id: "b" });
  };
  const checked = assert.rejects(session.getState().selectMembership("a"), isStale);
  await session.getState().selectMembership("b");
  gate.resolve(json({ access_token: "a" }));
  await checked;
  assert.equal(api.readStoredSession().accessToken, "b");
  assert.equal(session.getState().membershipId, "b");
});

test("obsolete profile mutation cannot resurrect an old user", async () => {
  const { session, start } = setup();
  start();
  const gate = deferred();
  globalThis.fetch = () => gate.promise;
  const checked = assert.rejects(session.getState().updateProfile({ name: "old" }), isStale);
  start("b");
  gate.resolve(json({ id: "a" }));
  await checked;
  assert.equal(session.getState().user, null);
  assert.equal(session.getState().isLoading, false);
});

for (const mode of ["noWindow", "blockedGetter", "getItem", "setItem", "removeItem", "malformed"]) {
  test(`safe session persist (${mode}) hydrates, authenticates and clears without throwing`, async () => {
    const storage = memoryStorage(mode === "malformed" ? [
      ["aicolab-session-cache", "{broken"], ["aicolab_session", "{broken"],
    ] : []);
    if (["getItem", "setItem", "removeItem"].includes(mode)) storage.failures.add(mode);
    const { api, session, permissions, start } = setup({
      storage, noWindow: mode === "noWindow", blockedGetter: mode === "blockedGetter",
    });
    assert.equal(session.getState().hasHydrated, true);
    assert.equal(session.persist.hasHydrated(), true);
    start();
    globalThis.fetch = async (url, options) => {
      assert.equal(options.headers.get("Authorization"), "Bearer a");
      return json(url.endsWith("/identity") ?
        { membership_id: "m-a", permissions: ["course:read"] } : { id: "u" });
    };
    await Promise.all([permissions.getState().loadPermissions(), session.getState().loadCurrentUser()]);
    assert.equal(permissions.getState().hasPermission("course:read"), true);
    assert.equal(session.getState().user.id, "u");
    assert.doesNotThrow(() => session.getState().clearSession());
    storage.failures.clear();
    assert.equal(api.readStoredSession().accessToken, null);
    assert.equal(session.getState().accessToken, null);
    assert.equal(permissions.getState().hasPermission("course:read"), false);
    assert.doesNotThrow(() => session.getState().clearPersistedState());
  });
}

test("failed token write uses new in-memory tokens, never stale disk credentials", async () => {
  const { api, storage, start } = setup();
  start("a");
  storage.failures.add("setItem");
  start("b");
  storage.failures.clear();
  assert.equal(JSON.parse(storage.getItem("aicolab_session")).accessToken, "a");
  assert.equal(api.readStoredSession().accessToken, "b");
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.headers.get("Authorization"), "Bearer b");
    return json({});
  };
  assert.equal((await api.apiFetch("/test")).status, 200);
});

test("refresh still works when storage becomes unavailable after login", async () => {
  const { api, session, storage, start } = setup();
  start("a", 1);
  storage.failures.add("getItem");
  storage.failures.add("setItem");
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/refresh")) {
      return json({ access_token: "new", expires_at: Date.now() / 1000 + 3600 });
    }
    assert.equal(options.headers.get("Authorization"), "Bearer new");
    return json({});
  };
  assert.equal((await api.apiFetch("/test")).status, 200);
  assert.equal(session.getState().accessToken, "new");
  assert.equal(api.readStoredSession().accessToken, "new");
});

test("profile cache hydrates only for the token session's membership and excludes credentials", async () => {
  for (const membershipId of ["m-a", "m-other"]) {
    const storage = memoryStorage([
      ["aicolab_session", JSON.stringify({
        accessToken: "a", refreshToken: "r-a", expiresAt: Date.now() / 1000 + 3600,
        membershipId: "m-a", organizationId: "o-a",
      })],
      ["aicolab-session-cache", JSON.stringify({ version: 1, state: {
        user: { id: "cached" }, membershipId, accessToken: "must-not-merge",
      } })],
    ]);
    const { session } = setup({ storage });
    assert.equal(session.getState().accessToken, "a");
    assert.equal(session.getState().user?.id ?? null, membershipId === "m-a" ? "cached" : null);
    assert.equal(session.getState().hasHydrated, true);
    assert.deepEqual(Object.keys(JSON.parse(storage.getItem("aicolab-session-cache")).state).sort(),
      ["membershipId", "user"]);
  }
});
