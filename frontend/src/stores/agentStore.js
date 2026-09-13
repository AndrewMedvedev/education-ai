import { create } from "zustand";
import {
  askEditorAgent,
  askInterviewerAgent,
  askMentorAgent,
} from "../utils/api";

const MAX_MESSAGE_LENGTH = 10_000;
const REQUEST_TIMEOUT_MS = 120_000;
const requestControllers = new Map();
let messageSequence = 0;

/**
 * @typedef {"interviewer" | "editor" | "mentor"} AgentType
 * @typedef {"idle" | "loading" | "success" | "error"} AgentStatus
 * @typedef {{ id: string, role: "user" | "assistant", text: string }} AgentMessage
 * @typedef {{
 *   agent: AgentType,
 *   courseId: string,
 *   chatId: string | null,
 *   messages: AgentMessage[],
 *   status: AgentStatus,
 *   error: string,
 *   activeRequestId: number | null
 * }} AgentConversation
 * @typedef {{
 *   hasStarted: boolean,
 *   isGenerating: boolean,
 *   taskId: string | null,
 *   generatedCourseId: string | null,
 *   status: string,
 *   courseStatus: string,
 *   progress: number,
 *   error: string,
 *   startedAt: string | null
 * }} AgentGenerationState
 */

function createMessage(role, text) {
  messageSequence += 1;
  return {
    id: `agent-message-${Date.now()}-${messageSequence}`,
    role,
    text: String(text),
  };
}

function normalizeUserContent(value) {
  const content = String(value ?? "")
    .replace(/\0/g, "")
    .replace(/[\u0001-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .trim();

  if (!content) {
    throw new Error("Введите сообщение.");
  }
  if (content.length > MAX_MESSAGE_LENGTH) {
    throw new Error(
      `Сообщение слишком длинное. Максимум — ${MAX_MESSAGE_LENGTH} символов.`,
    );
  }
  return content;
}

function getPublicError(error) {
  const statusMessages = {
    401: "Сессия истекла. Войдите заново.",
    403: "Недостаточно прав для обращения к этому ИИ-агенту.",
    422: "Запрос содержит некорректные данные. Обновите страницу и попробуйте снова.",
    429: "Слишком много запросов. Подождите и попробуйте снова.",
  };
  if (statusMessages[error?.status]) return statusMessages[error.status];
  if (Number(error?.status) >= 500) {
    return "ИИ-сервис временно недоступен. Попробуйте позже.";
  }
  return (
    error?.userMessage ||
    error?.message ||
    "ИИ-сервис временно недоступен. Попробуйте позже."
  );
}

function getConversation(state, key, agent, courseId) {
  return (
    state.conversations[key] || {
      agent,
      courseId,
      chatId: null,
      messages: [],
      status: "idle",
      error: "",
      activeRequestId: null,
    }
  );
}

export const createInitialGenerationState = () => ({
  hasStarted: false,
  isGenerating: false,
  taskId: null,
  generatedCourseId: null,
  status: "Жду ответы в чате",
  courseStatus: "",
  progress: 0,
  error: "",
  startedAt: null,
});

function normalizeProgress(value) {
  return Math.min(100, Math.max(0, Math.round(Number(value) || 0)));
}

function callAgent(agent, payload, options) {
  if (agent === "interviewer") {
    return askInterviewerAgent(payload, options);
  }
  if (agent === "mentor") {
    return askMentorAgent(payload, options);
  }
  if (agent === "editor") {
    return askEditorAgent(payload, options);
  }
  throw new Error("Неизвестный тип ИИ-агента.");
}

export const createAgentConversationKey = (agent, courseId, contextId = "") =>
  [agent, courseId || "missing-course", contextId].join(":");

export const useAgentStore = create((set, get) => ({
  /** @type {Record<string, AgentConversation>} */
  conversations: {},
  /** @type {Record<string, AgentGenerationState>} */
  generations: {},

  initializeConversation: ({ key, agent, courseId, initialMessage = "" }) => {
    set((state) => {
      if (state.conversations[key]) return state;
      return {
        conversations: {
          ...state.conversations,
          [key]: {
            agent,
            courseId,
            chatId: null,
            messages: initialMessage
              ? [createMessage("assistant", initialMessage)]
              : [],
            status: "idle",
            error: "",
            activeRequestId: null,
          },
        },
      };
    });
  },

  setChatId: (key, chatId) => {
    set((state) => {
      const conversation = state.conversations[key];
      if (!conversation) return state;
      return {
        conversations: {
          ...state.conversations,
          [key]: {
            ...conversation,
            chatId: chatId || null,
          },
        },
      };
    });
  },

  appendMessage: (key, role, text) => {
    if (!String(text ?? "").trim()) return;
    set((state) => {
      const conversation = state.conversations[key];
      if (!conversation) return state;
      return {
        conversations: {
          ...state.conversations,
          [key]: {
            ...conversation,
            messages: [
              ...conversation.messages,
              createMessage(role, String(text).trim()),
            ],
          },
        },
      };
    });
  },

  clearConversation: (key) => {
    requestControllers.get(key)?.abort();
    requestControllers.delete(key);
    set((state) => {
      const conversations = { ...state.conversations };
      const generations = { ...state.generations };
      delete conversations[key];
      delete generations[key];
      return { conversations, generations };
    });
  },

  cancelRequest: (key) => {
    requestControllers.get(key)?.abort();
    requestControllers.delete(key);
    set((state) => {
      const conversation = state.conversations[key];
      if (!conversation) return state;
      return {
        conversations: {
          ...state.conversations,
          [key]: {
            ...conversation,
            status: "idle",
            activeRequestId: null,
          },
        },
      };
    });
  },

  getGeneration: (key) =>
    get().generations[key] || createInitialGenerationState(),

  setGeneration: (key, patch) => {
    if (!key) return;
    set((state) => {
      const current = state.generations[key] || createInitialGenerationState();
      const nextPatch =
        typeof patch === "function" ? patch(current) || {} : { ...patch };
      if (Object.prototype.hasOwnProperty.call(nextPatch, "progress")) {
        nextPatch.progress = normalizeProgress(nextPatch.progress);
      }
      return {
        generations: {
          ...state.generations,
          [key]: {
            ...current,
            ...nextPatch,
          },
        },
      };
    });
  },

  resetGeneration: (key) => {
    if (!key) return;
    set((state) => ({
      generations: {
        ...state.generations,
        [key]: createInitialGenerationState(),
      },
    }));
  },

  sendMessage: async ({
    key,
    agent,
    courseId,
    content,
    contentBlocks = [],
    editorPayload = {},
    emptyResponseMessage = "Агент вернул пустой ответ. Попробуйте ещё раз.",
    responseDisplayMessage,
  }) => {
    const normalizedContent = normalizeUserContent(content);
    if (!courseId) {
      throw new Error("Не указан курс для обращения к ИИ-агенту.");
    }

    requestControllers.get(key)?.abort();
    const controller = new AbortController();
    let didTimeout = false;
    const timeoutId = setTimeout(() => {
      didTimeout = true;
      controller.abort();
    }, REQUEST_TIMEOUT_MS);
    requestControllers.set(key, controller);
    const requestId = Date.now() + Math.random();
    const current = getConversation(get(), key, agent, courseId);

    set((state) => ({
      conversations: {
        ...state.conversations,
        [key]: {
          ...current,
          agent,
          courseId,
          messages: [
            ...current.messages,
            createMessage("user", normalizedContent),
          ],
          status: "loading",
          error: "",
          activeRequestId: requestId,
        },
      },
    }));

    try {
      const response = await callAgent(
        agent,
        {
          ...editorPayload,
          chat_id: current.chatId,
          course_id: courseId,
          role: "user",
          content: normalizedContent,
          content_blocks: Array.isArray(contentBlocks) ? contentBlocks : [],
        },
        { signal: controller.signal },
      );
      const latest = get().conversations[key];
      if (latest?.activeRequestId !== requestId) return response;

      const responseText =
        typeof response?.content === "string" ? response.content.trim() : "";
      const visibleResponseText =
        responseDisplayMessage === undefined
          ? responseText
          : String(
              typeof responseDisplayMessage === "function"
                ? responseDisplayMessage(response)
                : responseDisplayMessage,
            ).trim();
      set((state) => ({
        conversations: {
          ...state.conversations,
          [key]: {
            ...state.conversations[key],
            chatId: response?.chatId || current.chatId,
            messages:
              visibleResponseText || emptyResponseMessage
                ? [
                    ...state.conversations[key].messages,
                    createMessage(
                      "assistant",
                      visibleResponseText || emptyResponseMessage,
                    ),
                  ]
                : state.conversations[key].messages,
            status: "success",
            error: "",
            activeRequestId: null,
          },
        },
      }));
      return response;
    } catch (error) {
      const latest = get().conversations[key];
      if (latest?.activeRequestId !== requestId) return null;
      if (controller.signal.aborted && !didTimeout) return null;

      const errorMessage = didTimeout
        ? "ИИ-сервис не ответил вовремя. Попробуйте отправить сообщение ещё раз."
        : getPublicError(error);
      set((state) => ({
        conversations: {
          ...state.conversations,
          [key]: {
            ...state.conversations[key],
            status: "error",
            error: errorMessage,
            activeRequestId: null,
          },
        },
      }));
      throw error;
    } finally {
      clearTimeout(timeoutId);
      if (requestControllers.get(key) === controller) {
        requestControllers.delete(key);
      }
    }
  },
}));
