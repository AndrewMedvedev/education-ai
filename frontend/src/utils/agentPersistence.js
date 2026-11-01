import { intakeQuestions } from "../creator/creatorChatConfig";

export const MAX_MESSAGE_LENGTH = 10_000;
const MAX_CONVERSATIONS = 30;
const MAX_MESSAGES = 200;
const AGENTS = new Set(["interviewer", "module_interviewer", "lesson_interviewer", "editor", "mentor"]);
const isRecord = (value) => value !== null && typeof value === "object" &&
  (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
const isId = (value) => typeof value === "string" && Boolean(value.trim());
const text = (value) => typeof value === "string" ? value.slice(0, MAX_MESSAGE_LENGTH) : "";
const id = (value) => isId(value) ? value : null;
const nonnegative = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
const timestamp = (value) => typeof value === "string" && Number.isFinite(Date.parse(value)) ? value : null;
const entries = (value) => isRecord(value) ? Object.entries(value).filter(([key]) =>
  isId(key) && key !== "prototype" && !Object.hasOwn(Object.prototype, key),
) : [];

function conversation(value) {
  if (!isRecord(value) || !AGENTS.has(value.agent) || !isId(value.courseId)) return null;
  return {
    agent: value.agent,
    courseId: value.courseId,
    chatId: id(value.chatId),
    messages: (Array.isArray(value.messages) ? value.messages : [])
      .filter((message) => isRecord(message) && isId(message.id) &&
        ["user", "assistant"].includes(message.role) && typeof message.text === "string")
      .slice(-MAX_MESSAGES)
      .map((message) => ({ id: message.id, role: message.role, text: text(message.text) })),
    // Only history is restored, never a pending request, error or response action.
    status: "idle",
    error: "",
    activeRequestId: null,
  };
}

function creatorDraft(value) {
  if (!isRecord(value)) return null;
  const answers = isRecord(value.answers) ? value.answers : {};
  return {
    stepIndex: Number.isInteger(value.stepIndex) && value.stepIndex >= 0
      ? Math.min(value.stepIndex, intakeQuestions.length) : 0,
    answers: Object.fromEntries(intakeQuestions
      .filter(({ id }) => Object.hasOwn(answers, id) && typeof answers[id] === "string")
      .map(({ id }) => [id, text(answers[id])])),
    inputValue: text(value.inputValue),
    files: (Array.isArray(value.files) ? value.files : [])
      .filter((file) => isRecord(file) && isId(file.id) && isId(file.name))
      .slice(0, 5)
      .map((file) => ({
        id: file.id, name: text(file.name),
        sizeKb: nonnegative(file.sizeKb) ? file.sizeKb : 0,
        size: nonnegative(file.size) ? file.size : null,
        lastModified: nonnegative(file.lastModified) ? file.lastModified : null,
      })),
  };
}

function generation(value, defaults) {
  if (!isRecord(value)) return null;
  return {
    ...defaults,
    hasStarted: value.hasStarted === true,
    isGenerating: value.isGenerating === true,
    taskId: id(value.taskId),
    generatedCourseId: id(value.generatedCourseId),
    status: typeof value.status === "string" ? text(value.status) : defaults.status,
    courseStatus: text(value.courseStatus),
    progress: nonnegative(value.progress) ? Math.min(100, Math.round(value.progress)) : 0,
    error: text(value.error),
    startedAt: timestamp(value.startedAt),
  };
}

// Used on both writes and same-version merge: valid JSON is not a valid schema.
export function sanitizeAgentState(state, generationDefaults) {
  const source = isRecord(state) ? state : {};
  const conversations = Object.fromEntries(entries(source.conversations)
    .map(([key, value]) => [key, conversation(value)])
    .filter(([, value]) => value).slice(-MAX_CONVERSATIONS));
  return {
    conversations,
    generations: Object.fromEntries(entries(source.generations)
      .filter(([key]) => Object.hasOwn(conversations, key))
      .map(([key, value]) => [key, generation(value, generationDefaults)])
      .filter(([, value]) => value)),
    interviewDrafts: Object.fromEntries(entries(source.interviewDrafts)
      .filter(([, value]) => typeof value === "string")
      .slice(-MAX_CONVERSATIONS).map(([key, value]) => [key, text(value)])),
    creatorDrafts: Object.fromEntries(entries(source.creatorDrafts)
      .map(([key, value]) => [key, creatorDraft(value)])
      .filter(([, value]) => value).slice(-MAX_CONVERSATIONS)),
  };
}

export function sanitizeGenerationJobs(state) {
  return {
    jobs: Object.fromEntries(entries(isRecord(state) ? state.jobs : null)
      .filter(([key, job]) => isRecord(job) && job.key === key &&
        ["module", "lesson"].includes(job.kind) && isId(job.courseId) &&
        (job.kind !== "lesson" || isId(job.moduleId)) &&
        ["running", "done", "error"].includes(job.status) && timestamp(job.startedAt) &&
        Array.isArray(job.knownIds) && job.knownIds.every(isId))
      .map(([key, job]) => [key, {
        key, kind: job.kind, courseId: job.courseId,
        moduleId: id(job.moduleId) || "",
        order: nonnegative(job.order) ? job.order : null,
        taskId: id(job.taskId), chatKey: id(job.chatKey),
        knownIds: [...job.knownIds], startedAt: timestamp(job.startedAt),
        status: job.status,
        resultId: id(job.resultId), resultTitle: text(job.resultTitle),
        lessonsCount: nonnegative(job.lessonsCount) ? Math.floor(job.lessonsCount) : 0,
        lastChangeAt: timestamp(job.lastChangeAt), error: text(job.error),
      }])),
  };
}
