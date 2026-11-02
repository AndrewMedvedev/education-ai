/* Own assessment requests independently of the lesson document. */
const DB_NAME = "lesson-practice-requests-v1";
const STORE = "requests";
const active = new Map();
const pendingStatuses = ["generating", "checking"];
const recoverInterrupted = (key, value) => {
  if (value && pendingStatuses.includes(value.status) &&
      !active.has(`${key}:generate`) && !active.has(`${key}:check`)) {
    return { ...value, status: "error", error: "Запрос прервался. Попробуйте ещё раз." };
  }
  return value;
};
const attemptId = (value) =>
  value?.generated?.practice_id ||
  value?.generated?.practiceId ||
  value?.generated?.id;

function database() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore(STORE, { keyPath: "key" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Read-modify-write in one transaction: draft/read acknowledgements must not
// overwrite a check response arriving at the same time.
async function record(key, update) {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const transaction = db.transaction(
        STORE,
        update ? "readwrite" : "readonly",
      );
      const store = transaction.objectStore(STORE);
      const request = store.get(key);
      let value;
      request.onsuccess = () => {
        value = request.result || null;
        if (update) {
          value = update(value);
          if (value) store.put(value);
          else store.delete(key);
        }
      };
      transaction.oncomplete = () => resolve(value);
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    db.close();
  }
}

async function hasPendingRequests() {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction(STORE).objectStore(STORE).getAll();
      request.onsuccess = () =>
        resolve(
          request.result.some((value) =>
            pendingStatuses.includes(value.status),
          ),
        );
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

self.addEventListener("install", (event) => {
  // Upgrade on reload when idle, but never replace the owner of an active fetch.
  event.waitUntil(
    hasPendingRequests().then((pending) => {
      if (!pending) return self.skipWaiting();
    }),
  );
});
self.addEventListener("activate", (event) =>
  event.waitUntil(self.clients.claim()),
);
self.addEventListener("message", (event) => {
  const { type, key, expectedAttemptId, answers } = event.data || {};
  const port = event.ports[0];
  if (!port) return;
  let work;
  if (type === "READ_LESSON_PRACTICE") work = record(key, (value) => recoverInterrupted(key, value));
  if (type === "OPEN_LESSON_ASSESSMENT") {
    work = record(key, (value) => {
      value = recoverInterrupted(key, value);
      return value?.result && value.viewed ? null : value;
    });
  }
  if (type === "ASSESSMENT_ANSWERS") {
    work = record(key, (value) =>
      value && attemptId(value) === expectedAttemptId && !value.result
        ? { ...value, answers }
        : value,
    );
  }
  if (type === "ASSESSMENT_VIEWED") {
    work = record(key, (value) =>
      value?.result && attemptId(value) === expectedAttemptId
        ? { ...value, viewed: true }
        : value,
    );
  }
  if (type === "FINISH_LESSON_ASSESSMENT") {
    work = record(key, (value) =>
      value?.result && attemptId(value) === expectedAttemptId ? null : value,
    );
  }
  if (!work) return;
  event.waitUntil(
    work.then(
      (value) => port.postMessage({ value }),
      () =>
        port.postMessage({
          error: "Не удалось сохранить или восстановить состояние задания.",
        }),
    ),
  );
});

async function execute(request, key, operation) {
  const previous = await record(key);
  const saved =
    operation === "generate" ? previous?.generated : previous?.result;
  if (saved) {
    return new Response(JSON.stringify(saved), {
      headers: { "Content-Type": "application/json" },
    });
  }
  if (pendingStatuses.includes(previous?.status)) {
    return new Response(
      JSON.stringify({
        detail: "Запрос уже выполняется. Дождитесь результата.",
      }),
      {
        status: 409,
        headers: { "Content-Type": "application/json" },
      },
    );
  }
  await record(key, (current) => ({
    ...current,
    key,
    status: operation === "generate" ? "generating" : "checking",
    startedAt: Date.now(),
    error: "",
  }));
  try {
    const headers = new Headers(request.headers);
    headers.delete("X-Lesson-Practice-Key");
    headers.delete("X-Lesson-Practice-Operation");
    // A reload aborts the document's request, not this worker-owned fetch.
    const response = await fetch(
      new Request(request, { headers, signal: new AbortController().signal }),
    );
    if (!response.ok) {
      const data = await response.clone().json().catch(() => null);
      const message =
        (typeof data?.detail === "string" && data.detail) ||
        (typeof data?.error?.message === "string" && data.error.message) ||
        `Не удалось выполнить запрос задания (HTTP ${response.status}).`;
      await record(key, (current) => ({
        ...current,
        status: "error",
        error: message,
      }));
      return new Response(JSON.stringify({ detail: message }), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }
    const data = await response.clone().json();
    await record(key, (current) => ({
      ...current,
      status: "ready",
      error: "",
      ...(operation === "generate"
        ? { generated: data, result: null, answers: {}, viewed: false }
        : { result: data, viewed: false }),
    }));
    return response;
  } catch (error) {
    await record(key, (current) => ({
      ...current,
      status: "error",
      error: error.message,
    }));
    return new Response(JSON.stringify({ detail: error.message }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const key = request.headers.get("X-Lesson-Practice-Key");
  const operation = request.headers.get("X-Lesson-Practice-Operation");
  const path = new URL(request.url).pathname;
  const matches =
    operation === "generate"
      ? /\/agent\/(?:practices|tests)\/[^/]+\/[^/]+\/?$/.test(path)
      : operation === "check" &&
        /\/agent\/check\/(?:practices|tests)\/[^/]+\/?$/.test(path);
  if (request.method !== "POST" || !key || !matches) return;
  const activeKey = `${key}:${operation}`;
  let work = active.get(activeKey);
  if (!work) {
    work = execute(request, key, operation);
    active.set(activeKey, work);
    work.finally(() => active.delete(activeKey)).catch(() => {});
  }
  event.waitUntil(
    work.then(
      () => {},
      () => {},
    ),
  );
  event.respondWith(work.then((response) => response.clone()));
});
