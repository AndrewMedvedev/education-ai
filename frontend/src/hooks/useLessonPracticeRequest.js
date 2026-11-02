import { useCallback, useEffect, useRef, useState } from "react";
import { useSessionStore } from "../stores/sessionStore";
import {
  generateLessonPractice,
  fetchLessonPractice,
  fetchPracticeGeneration,
  startPracticeGeneration,
  checkLessonPractice,
  generateLessonTest,
  checkLessonTest,
} from "../utils/api";
import { reloadScope } from "../utils/reloadPersistence";
import { getReloadScope } from "../utils/reloadScope";
import { pollPracticeGeneration } from "../utils/practiceGenerationPoll";
import {
  ensurePracticeWorker,
  readPracticeRequest,
  practiceRecordKey,
  practiceRequestOptions,
  openAssessment,
  saveAssessmentAnswers,
  markAssessmentViewed,
  finishAssessment,
  discardStalePractice,
  saveGeneratedPractice,
} from "../utils/lessonPracticeRequests";

const empty = {
  assignment: null,
  practiceId: null,
  result: null,
  answers: {},
  status: "idle",
  error: "",
};
const pending = ["generating", "checking"];

function restored(record) {
  if (!record) return empty;
  const data = record.generated;
  return {
    assignment: data?.practice || data?.assignment || data?.test || null,
    practiceId: data?.practice_id || data?.practiceId || data?.id || null,
    result: record.result || null,
    answers: record.answers || {},
    status: record.status,
    error: record.error || "",
  };
}

export function useLessonPracticeRequest(
  moduleId,
  lessonId,
  kind = "practice",
) {
  const scope = useSessionStore(reloadScope);
  const key = practiceRecordKey(scope, moduleId, lessonId, kind);
  const [state, setState] = useState({ ...empty, key, status: "restoring" });
  const currentKey = useRef(key);
  const sending = useRef(false);
  const opening = useRef(null);
  currentKey.current = key;
  const visible = state.key === key ? state : { ...empty, status: "restoring" };
  const isCurrent = useCallback(
    () => currentKey.current === key && getReloadScope() === scope,
    [key, scope],
  );

  const refresh = useCallback(async () => {
    const record = await readPracticeRequest(key);
    if (isCurrent()) setState({ ...restored(record), key });
  }, [key, isCurrent]);

  const applyPracticeGeneration = useCallback(async (job) => {
    if (!isCurrent()) return;
    if (job?.status === "succeeded" && job.practice_id && job.practice) {
      const record = await saveGeneratedPractice(key, job);
      if (isCurrent()) setState({ ...restored(record), key });
    } else if (["queued", "running"].includes(job?.status)) {
      setState((previous) => ({ ...previous, key, status: "generating", error: "" }));
    } else {
      setState((previous) => ({ ...previous, key, status: "error", error: "Не удалось завершить генерацию практики. Попробуйте ещё раз." }));
    }
  }, [key, isCurrent]);

  useEffect(() => {
    if (!scope || !moduleId || !lessonId) return;
    let cancelled = false;
    // Reuse the initial open in React StrictMode; consuming a viewed result
    // happens only on entering this assessment, not on every state change.
    if (opening.current?.key !== key) {
      opening.current = { key, promise: openAssessment(key) };
    }
    opening.current.promise
      .then(async (record) => {
        const savedId = restored(record).practiceId;
        if (kind === "practice" && savedId && !pending.includes(record.status)) {
          try {
            const remote = await fetchLessonPractice(moduleId, lessonId);
            if (cancelled || !isCurrent()) return;
            if (remote && typeof remote === "object" &&
                Object.hasOwn(remote, "practice_id") && remote.practice_id !== savedId) {
              record = await discardStalePractice(key, savedId);
            }
          } catch {
            // Keep the local copy when the server cannot be reached.
          }
        }
        if (kind === "practice" && !restored(record).practiceId) {
          try {
            const job = await fetchPracticeGeneration(moduleId, lessonId);
            if (cancelled || !isCurrent()) return;
            if (job?.status !== "idle") {
              await applyPracticeGeneration(job);
              return;
            }
          } catch {
            // Allow an explicit retry when the status endpoint is unavailable.
          }
        }
        if (!cancelled && isCurrent()) setState({ ...restored(record), key });
      })
      .catch((error) => {
        if (!cancelled && isCurrent())
          setState({ ...empty, key, status: "error", error: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, [key, scope, moduleId, lessonId, kind, isCurrent, applyPracticeGeneration]);

  useEffect(() => {
    if (!scope || !pending.includes(visible.status) || (kind === "practice" && visible.status === "generating")) return;
    let cancelled = false;
    let timer;
    const poll = async () => {
      try {
        const record = await readPracticeRequest(key);
        if (cancelled || !isCurrent()) return;
        // Do not replace optimistic pending UI with the previous record before
        // the worker has accepted the request.
        if (!sending.current || pending.includes(record?.status)) {
          setState({ ...restored(record), key });
        }
        if (sending.current || pending.includes(record?.status))
          timer = setTimeout(poll, 1500);
      } catch (error) {
        if (!cancelled && isCurrent())
          setState((previous) => ({
            ...previous,
            status: "error",
            error: error.message,
          }));
      }
    };
    timer = setTimeout(poll, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key, scope, visible.status, isCurrent, kind]);

  useEffect(() => {
    if (!scope || kind !== "practice" || visible.status !== "generating") return;
    return pollPracticeGeneration({
      load: () => fetchPracticeGeneration(moduleId, lessonId),
      apply: applyPracticeGeneration,
      isCurrent,
      isSending: () => sending.current,
      onError: (error, terminal) => setState((previous) => ({
        ...previous,
        ...(terminal ? { status: "error" } : {}),
        error: terminal ? (error.userMessage || error.message) : "Не удалось получить состояние. Повторяем запрос…",
      })),
    });
  }, [scope, kind, visible.status, moduleId, lessonId, isCurrent, applyPracticeGeneration]);

  const send = async (operation, payload) => {
    if (
      !scope ||
      sending.current ||
      ["restoring", "finishing", ...pending].includes(visible.status)
    )
      return null;
    sending.current = true;
    setState((previous) => ({
      ...previous,
      key,
      error: "",
      status: operation === "generate" ? "generating" : "checking",
    }));
    try {
      await ensurePracticeWorker();
      if (!isCurrent()) return null;
      if (operation === "generate" && kind === "practice") {
        const job = await startPracticeGeneration(moduleId, lessonId);
        await applyPracticeGeneration(job);
        return job;
      }
      const options = practiceRequestOptions(key, operation);
      let response;
      if (operation === "generate") {
        response = await (
          kind === "test" ? generateLessonTest : generateLessonPractice
        )(moduleId, lessonId, options);
      } else if (kind === "test") {
        response = await checkLessonTest(visible.practiceId, payload, options);
      } else {
        response = await checkLessonPractice(
          visible.practiceId,
          visible.assignment,
          payload,
          options,
        );
      }
      await refresh();
      return isCurrent() ? response : null;
    } catch (error) {
      if (isCurrent()) {
        const record = await readPracticeRequest(key).catch(() => null);
        if (isCurrent())
          setState({
            ...restored(record),
            key,
            ...(record && pending.includes(record.status)
              ? {}
              : { status: "error", error: error.userMessage || error.message }),
          });
      }
      return null;
    } finally {
      sending.current = false;
    }
  };

  const reportError = useCallback(
    (error) => {
      if (isCurrent())
        setState((previous) => ({ ...previous, error: error.message }));
    },
    [isCurrent],
  );

  const setAnswers = (answers) => {
    if (
      !visible.practiceId ||
      visible.result ||
      pending.includes(visible.status)
    )
      return;
    const next =
      typeof answers === "function" ? answers(visible.answers) : answers;
    setState((previous) => ({ ...previous, answers: next }));
    saveAssessmentAnswers(key, visible.practiceId, next).catch(reportError);
  };

  const markViewed = useCallback(() => {
    if (visible.result && visible.practiceId && isCurrent()) {
      markAssessmentViewed(key, visible.practiceId).catch(reportError);
    }
  }, [key, visible.result, visible.practiceId, isCurrent, reportError]);

  const finish = async () => {
    if (!visible.result || sending.current || !isCurrent()) return;
    setState((previous) => ({ ...previous, status: "finishing" }));
    try {
      const record = await finishAssessment(key, visible.practiceId);
      if (isCurrent()) setState({ ...restored(record), key });
    } catch (error) {
      if (isCurrent())
        setState((previous) => ({
          ...previous,
          status: "ready",
          error: error.message,
        }));
    }
  };

  return {
    ...visible,
    isRestoring: ["restoring", "finishing"].includes(visible.status),
    isLoading: visible.status === "generating",
    isChecking: visible.status === "checking",
    generate: () => send("generate"),
    check: (payload) => send("check", payload),
    setAnswers,
    markViewed,
    finish,
  };
}
