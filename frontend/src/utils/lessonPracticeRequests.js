let registration;

export async function ensurePracticeWorker() {
  if (!navigator.serviceWorker || !window.isSecureContext) {
    throw new Error(
      "Для сохранения запросов заданий необходим HTTPS или localhost и поддержка Service Worker.",
    );
  }
  if (!registration) {
    registration = navigator.serviceWorker
      .register("/lesson-practice-worker.js", {
        scope: "/",
        updateViaCache: "none",
      })
      .then(async (value) => {
        const installing = value.installing;
        if (
          installing &&
          !["activated", "installed", "redundant"].includes(installing.state)
        ) {
          await new Promise((resolve) => {
            installing.addEventListener("statechange", () => {
              if (
                ["activated", "installed", "redundant"].includes(
                  installing.state,
                )
              )
                resolve();
            });
          });
        }
        // skipWaiting/claim may still be completing after the installed event.
        if (value.installing?.state === "installed" || value.waiting) {
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        return value;
      })
      .catch((error) => {
        registration = null;
        throw error;
      });
  }
  await registration;
  await navigator.serviceWorker.ready;
  if (!navigator.serviceWorker.controller) {
    await new Promise((resolve, reject) => {
      const done = () => {
        clearTimeout(timer);
        navigator.serviceWorker.removeEventListener(
          "controllerchange",
          changed,
        );
        resolve();
      };
      const changed = () => {
        if (navigator.serviceWorker.controller) done();
      };
      const timer = setTimeout(() => {
        navigator.serviceWorker.removeEventListener(
          "controllerchange",
          changed,
        );
        reject(
          new Error(
            "Не удалось подключить сохранение запросов заданий. Обновите страницу.",
          ),
        );
      }, 15000);
      navigator.serviceWorker.addEventListener("controllerchange", changed);
      changed();
    });
  }
}

export async function assessmentMessage(type, key, payload = {}) {
  await ensurePracticeWorker();
  return new Promise((resolve, reject) => {
    const channel = new MessageChannel();
    const timer = setTimeout(() => {
      channel.port1.close();
      reject(new Error("Не удалось восстановить состояние задания."));
    }, 10000);
    channel.port1.onmessage = ({ data }) => {
      clearTimeout(timer);
      channel.port1.close();
      if (data.error) reject(new Error(data.error));
      else resolve(data.value);
    };
    navigator.serviceWorker.controller.postMessage({ type, key, ...payload }, [
      channel.port2,
    ]);
  });
}

export function practiceRequestOptions(key, operation) {
  return {
    headers: {
      "X-Lesson-Practice-Key": key,
      "X-Lesson-Practice-Operation": operation,
    },
  };
}

export const readPracticeRequest = (key) =>
  assessmentMessage("READ_LESSON_PRACTICE", key);
export const openAssessment = (key) =>
  assessmentMessage("OPEN_LESSON_ASSESSMENT", key);
export const saveAssessmentAnswers = (key, expectedAttemptId, answers) =>
  assessmentMessage("ASSESSMENT_ANSWERS", key, { expectedAttemptId, answers });
export const markAssessmentViewed = (key, expectedAttemptId) =>
  assessmentMessage("ASSESSMENT_VIEWED", key, { expectedAttemptId });
export const finishAssessment = (key, expectedAttemptId) =>
  assessmentMessage("FINISH_LESSON_ASSESSMENT", key, { expectedAttemptId });
export const discardStalePractice = (key, expectedAttemptId) =>
  assessmentMessage("DISCARD_STALE_PRACTICE", key, { expectedAttemptId });

export const practiceRecordKey = (
  scope,
  moduleId,
  lessonId,
  kind = "practice",
) =>
  encodeURIComponent(
    JSON.stringify(
      kind === "test"
        ? [scope, moduleId, lessonId, "test"]
        : [scope, moduleId, lessonId],
    ),
  );
