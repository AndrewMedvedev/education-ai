import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

test("practice worker preserves an upstream HTML error status and records a readable error", async () => {
  const source = await readFile(new URL("../../public/lesson-practice-worker.js", import.meta.url), "utf8");
  const context = vm.createContext({
    self: { addEventListener() {} },
    Response, Request, Headers, AbortController, URL,
    fetch: async () => new Response("<html>Bad Gateway</html>", { status: 502 }),
  });
  vm.runInContext(source, context);
  vm.runInContext(`
    let savedRecord = null;
    record = async (key, update) => {
      if (update) savedRecord = update(savedRecord);
      return savedRecord;
    };
  `, context);
  const response = await vm.runInContext(
    `execute(new Request('https://example.test/api/v1/agent/practices/m/l', { method: 'POST' }), 'key', 'generate')`,
    context,
  );
  assert.equal(response.status, 502);
  assert.match((await response.json()).detail, /HTTP 502/);
  assert.match(vm.runInContext("savedRecord.error", context), /HTTP 502/);
  assert.equal(vm.runInContext("savedRecord.status", context), "error");
});

test("a pending request without a live worker operation can be retried", async () => {
  const source = await readFile(new URL("../../public/lesson-practice-worker.js", import.meta.url), "utf8");
  const context = vm.createContext({ self: { addEventListener() {} }, Response, Request, Headers, AbortController, URL });
  vm.runInContext(source, context);
  assert.equal(vm.runInContext(`recoverInterrupted('key', {status: 'generating'}).status`, context), "error");
  assert.equal(vm.runInContext(`active.set('key:generate', {}); recoverInterrupted('key', {status: 'generating'}).status`, context), "generating");
});

test("discarding a stale practice preserves a newer or pending attempt", async () => {
  const source = await readFile(new URL("../../public/lesson-practice-worker.js", import.meta.url), "utf8");
  const handlers = {};
  const context = vm.createContext({ self: { addEventListener(type, fn) { handlers[type] = fn; } }, Response, Request, Headers, AbortController, URL });
  vm.runInContext(source, context);
  vm.runInContext(`let saved = null; record = async (key, update) => saved = update(saved)`, context);
  async function discard(value, expected) {
    context.input = value;
    vm.runInContext("saved = input", context);
    let work;
    handlers.message({ data: { type: "DISCARD_STALE_PRACTICE", key: "key", expectedAttemptId: expected }, ports: [{ postMessage() {} }], waitUntil(p) { work = p; } });
    await work;
    return vm.runInContext("saved", context);
  }
  assert.equal(await discard({ status: "ready", generated: { practice_id: "old" } }, "old"), null);
  assert.equal((await discard({ status: "ready", generated: { practice_id: "new" } }, "old")).generated.practice_id, "new");
  assert.equal((await discard({ status: "checking", generated: { practice_id: "old" } }, "old")).status, "checking");
});
