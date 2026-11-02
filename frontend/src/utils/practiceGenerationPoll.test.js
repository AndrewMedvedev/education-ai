import test from "node:test";
import assert from "node:assert/strict";
import { pollPracticeGeneration } from "./practiceGenerationPoll.js";

function clock() {
  const jobs = [];
  return {
    jobs,
    schedule(fn, delay) { const item = { fn, delay }; jobs.push(item); return item; },
    cancel(item) { const i = jobs.indexOf(item); if (i >= 0) jobs.splice(i, 1); },
    async tick() { const item = jobs.shift(); assert.ok(item); await item.fn(); return item.delay; },
  };
}

test("polls running job after transient failure and stops after saved result", async () => {
  const timers = clock();
  const seen = [];
  let calls = 0, errors = 0;
  const stop = pollPracticeGeneration({
    load: async () => { calls++; if (calls === 1) throw new Error("offline"); return calls === 2 ? { status: "running" } : { status: "succeeded", practice_id: "p" }; },
    apply: async (job) => seen.push(job), isCurrent: () => true, isSending: () => false,
    onError: () => errors++, schedule: timers.schedule, cancel: timers.cancel,
  });
  assert.equal(await timers.tick(), 3000);
  assert.equal(await timers.tick(), 5000);
  assert.equal(await timers.tick(), 3000);
  assert.equal(errors, 1);
  assert.deepEqual(seen.map((x) => x.status), ["running", "succeeded"]);
  assert.equal(timers.jobs.length, 0);
  stop();
});

test("a late response after logout or unmount cannot be applied", async () => {
  const timers = clock();
  let resolve, applied = false, current = true;
  const response = new Promise((done) => { resolve = done; });
  const stop = pollPracticeGeneration({ load: () => response, apply: () => { applied = true; },
    isCurrent: () => current, isSending: () => false, onError: () => {}, schedule: timers.schedule, cancel: timers.cancel });
  const pending = timers.tick();
  current = false;
  stop();
  resolve({ status: "succeeded" });
  await pending;
  assert.equal(applied, false);
  assert.equal(timers.jobs.length, 0);
});

test("a permission error stops polling instead of looping indefinitely", async () => {
  const timers = clock();
  let terminal = false;
  pollPracticeGeneration({ load: async () => { throw Object.assign(new Error("denied"), { status: 403 }); },
    apply: () => {}, isCurrent: () => true, isSending: () => false,
    onError: (_, value) => { terminal = value; }, schedule: timers.schedule, cancel: timers.cancel });
  await timers.tick();
  assert.equal(terminal, true);
  assert.equal(timers.jobs.length, 0);
});
