import assert from "node:assert/strict";
import { test } from "node:test";
import { createDetailLoader } from "./detailLoader.js";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function unexpected() {
  assert.fail("Unexpected callback");
}

test("deduplicates pending and successful runs, including reentrant calls", async () => {
  const loader = createDetailLoader();
  const response = deferred();
  const applied = [];
  let calls = 0;
  assert.equal(loader.getStatus("A"), "idle");
  const first = loader.run("A", () => {
    calls += 1;
    assert.equal(loader.run("A", unexpected, unexpected), first);
    return response.promise;
  }, (value) => applied.push(value));
  assert.equal(loader.getStatus("A"), "pending");
  assert.equal(loader.run("A", unexpected, unexpected), first);
  response.resolve({ id: "A" });
  assert.deepEqual(await first, { id: "A" });
  assert.equal(calls, 1);
  assert.deepEqual(applied, [{ id: "A" }]);
  assert.equal(loader.getStatus("A"), "success");
  assert.equal(loader.run("A", unexpected, unexpected), first);
});

test("different keys can finish out of order independently", async () => {
  const loader = createDetailLoader();
  const a = deferred();
  const b = deferred();
  const applied = [];
  const first = loader.run("A", () => a.promise, (value) => applied.push(value));
  const second = loader.run("B", () => b.promise, (value) => applied.push(value));
  b.resolve("B");
  await second;
  assert.equal(loader.getStatus("A"), "pending");
  assert.equal(loader.getStatus("B"), "success");
  a.resolve("A");
  await first;
  assert.deepEqual(applied, ["B", "A"]);
});

test("success is recorded only after asynchronous apply completes", async () => {
  const loader = createDetailLoader();
  const started = deferred();
  const applied = deferred();
  const pending = loader.run("A", () => "value", (value) => {
    assert.equal(value, "value");
    assert.equal(loader.getStatus("A"), "pending");
    started.resolve();
    return applied.promise;
  });
  await started.promise;
  assert.equal(loader.getStatus("A"), "pending");
  assert.equal(loader.run("A", unexpected, unexpected), pending);
  applied.resolve();
  await pending;
  assert.equal(loader.getStatus("A"), "success");
});

for (const value of [undefined, null, "", false, 0, [], {}]) {
  test(`empty result ${JSON.stringify(value)} is successful`, async () => {
    const loader = createDetailLoader();
    const applied = [];
    const pending = loader.run("A", () => value, (result) => applied.push(result));
    assert.equal(await pending, value);
    assert.deepEqual(applied, [value]);
    assert.equal(loader.getStatus("A"), "success");
    assert.equal(loader.run("A", unexpected, unexpected), pending);
  });
}

for (const phase of ["load", "apply"]) {
  for (const asynchronous of [false, true]) {
    test(`${phase} ${asynchronous ? "rejection" : "throw"} allows retry`, async () => {
      const loader = createDetailLoader();
      const error = new Error("failed");
      const fail = () => {
        if (asynchronous) return Promise.reject(error);
        throw error;
      };
      const pending = loader.run(
        "A",
        phase === "load" ? fail : () => "value",
        phase === "apply" ? fail : unexpected,
      );
      assert.equal(loader.run("A", unexpected, unexpected), pending);
      await assert.rejects(pending, (caught) => caught === error);
      assert.equal(loader.getStatus("A"), "error");
      const applied = [];
      await loader.run("A", () => "retry", (value) => applied.push(value));
      assert.deepEqual(applied, ["retry"]);
      assert.equal(loader.getStatus("A"), "success");
    });
  }
}

test("reset invalidates pending A → B → A even when old A finishes first", async () => {
  const loader = createDetailLoader();
  const oldA = deferred();
  const b = deferred();
  const newA = deferred();
  const applied = [];
  const first = loader.run("A", () => oldA.promise, unexpected);
  await Promise.resolve();
  loader.reset();
  assert.equal(loader.getStatus("A"), "idle");
  const second = loader.run("B", () => b.promise, unexpected);
  await Promise.resolve();
  loader.reset();
  const third = loader.run("A", () => newA.promise, (value) => applied.push(value));
  oldA.resolve("old A");
  b.resolve("old B");
  await Promise.all([first, second]);
  assert.equal(loader.getStatus("A"), "pending");
  assert.equal(loader.getStatus("B"), "idle");
  newA.resolve("new A");
  await third;
  assert.deepEqual(applied, ["new A"]);
  assert.equal(loader.getStatus("A"), "success");
});

test("stale rejection cannot replace the status of a successful retry", async () => {
  const loader = createDetailLoader();
  const old = deferred();
  const first = loader.run("A", () => old.promise, unexpected);
  const rejected = assert.rejects(first, /stale failure/);
  await Promise.resolve();
  loader.reset();
  await loader.run("A", () => "new", () => {});
  old.reject(new Error("stale failure"));
  await rejected;
  assert.equal(loader.getStatus("A"), "success");
});

test("reset during apply prevents stale success from replacing a new entry", async () => {
  const loader = createDetailLoader();
  const started = deferred();
  const applied = deferred();
  const first = loader.run("A", () => "old", () => {
    started.resolve();
    return applied.promise;
  });
  await started.promise;
  loader.reset();
  const response = deferred();
  const second = loader.run("A", () => response.promise, () => {});
  applied.resolve();
  await first;
  assert.equal(loader.getStatus("A"), "pending");
  response.resolve("new");
  await second;
  assert.equal(loader.getStatus("A"), "success");
});

test("reset before load starts skips stale callbacks", async () => {
  const loader = createDetailLoader();
  const pending = loader.run("A", unexpected, unexpected);
  loader.reset();
  await pending;
  assert.equal(loader.getStatus("A"), "idle");
});

test("forget invalidates only its key and permits manual reload after success", async () => {
  const loader = createDetailLoader();
  const old = deferred();
  const pending = loader.run("A", () => old.promise, unexpected);
  await loader.run("B", () => "B", () => {});
  loader.forget("A");
  assert.equal(loader.getStatus("A"), "idle");
  assert.equal(loader.getStatus("B"), "success");
  const applied = [];
  await loader.run("A", () => "new A", (value) => applied.push(value));
  old.resolve("old A");
  await pending;
  assert.deepEqual(applied, ["new A"]);
  assert.equal(loader.getStatus("A"), "success");
  loader.forget("A");
  await loader.run("A", () => "manual A", (value) => applied.push(value));
  assert.deepEqual(applied, ["new A", "manual A"]);
  loader.forget("missing");
  assert.equal(loader.getStatus("missing"), "idle");
});
