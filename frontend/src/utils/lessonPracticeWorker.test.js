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
