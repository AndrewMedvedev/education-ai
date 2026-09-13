import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "../creator/creator-chat.css";

import { intakeQuestions } from "../creator/creatorChatConfig";
import {
  createAgentConversationKey,
  createInitialGenerationState,
  useAgentStore,
} from "../stores/agentStore";
import {
  DOCUMENT_ALLOWED_EXTENSION,
  DOCUMENT_ALLOWED_EXTENSIONS_LABEL,
  DOCUMENT_MAX_SIZE_BYTES,
  fetchCourseStatus,
  saveDocument,
} from "../utils/api";
import { getLocalStorage } from "../utils/storage";

const MAX_FILES = 5;

const ACTIVE_CREATOR_COURSE_KEY = "course-generation:active-course";
const COURSE_GENERATION_POLLING_INTERVAL_MS = 10_000;
const COURSE_GENERATION_NOT_FOUND_GRACE_MS = 25 * 60 * 1000;
const PROGRESS_TICK_MS = 500;
const FAKE_PROGRESS_EASING_DURATION_MS = 30 * 60 * 1000;
const NOT_FOUND_STATUS = 404;

function createUuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (value) => {
    const random = Math.floor(Math.random() * 16);
    const digit = value === "x" ? random : (random & 0x3) | 0x8;
    return digit.toString(16);
  });
}

function getGenerationKey(courseId) {
  return `course-generation:${courseId}`;
}

function createCourseId() {
  return getLocalStorage()?.getItem(ACTIVE_CREATOR_COURSE_KEY) || createUuid();
}

function readGenerationState(courseId) {
  const storage = getLocalStorage();
  if (!storage || !courseId) return null;
  try {
    const value = JSON.parse(
      storage.getItem(getGenerationKey(courseId)) || "null",
    );
    return value?.courseId === courseId ? value : null;
  } catch {
    return null;
  }
}

function writeGenerationState(record) {
  const storage = getLocalStorage();
  if (!storage || !record?.courseId) return;
  storage.setItem(getGenerationKey(record.courseId), JSON.stringify(record));
  storage.setItem(ACTIVE_CREATOR_COURSE_KEY, record.courseId);
}

function clearGenerationState(courseId) {
  const storage = getLocalStorage();
  if (!storage || !courseId) return;
  storage.removeItem(getGenerationKey(courseId));
  if (storage.getItem(ACTIVE_CREATOR_COURSE_KEY) === courseId) {
    storage.removeItem(ACTIVE_CREATOR_COURSE_KEY);
  }
}

function estimateProgress(startedAt) {
  const started = Date.parse(startedAt || "");
  const elapsed = Number.isFinite(started) ? Date.now() - started : 0;
  const ratio = Math.max(0, elapsed) / FAKE_PROGRESS_EASING_DURATION_MS;
  return Math.min(
    95,
    Math.max(4, Math.round(95 * (1 - Math.exp(-ratio * 1.1)))),
  );
}

function parseMaybeJson(value) {
  if (typeof value !== "string") return value;
  const trimmed = value.trim();
  if (!trimmed || !/^[{[]/.test(trimmed)) return value;
  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
}

function getResponseSources(response) {
  return [
    response,
    parseMaybeJson(response?.content),
    response?.response,
    response?.data,
    response?.result,
  ].filter((item) => item && typeof item === "object");
}

function extractCourseId(response) {
  const sources = getResponseSources(response);
  const source = sources.find(
    (item) => item.course_id || item.courseId || item.course?.id,
  );
  return source?.course_id || source?.courseId || source?.course?.id || null;
}

function normalizeGenerationResponse(response) {
  const sources = getResponseSources(response);

  const taskId = sources.find(
    (item) => item.task_id || item.taskId || item.task || item.id,
  );
  const courseId = sources.find(
    (item) => item.course_id || item.courseId || item.course?.id,
  );
  const statusSource = sources.find(
    (item) =>
      item.status || item.course_status || item.courseStatus || item.state,
  );
  const startedSource = sources.find(
    (item) =>
      item.started_at || item.startedAt || item.created_at || item.createdAt,
  );
  const status = String(
    statusSource?.status ||
      statusSource?.course_status ||
      statusSource?.courseStatus ||
      statusSource?.state ||
      "",
  ).toLowerCase();
  const isGenerationStatus = ["in_generation", "generating", "queued"].includes(
    status,
  );
  const normalizedTaskId =
    taskId?.task_id || taskId?.taskId || taskId?.task || taskId?.id || null;
  const normalizedCourseId =
    courseId?.course_id || courseId?.courseId || courseId?.course?.id || null;

  if (!normalizedTaskId && !isGenerationStatus) return null;

  return {
    taskId: normalizedTaskId,
    courseId: normalizedCourseId,
    startedAt:
      startedSource?.started_at ||
      startedSource?.startedAt ||
      startedSource?.created_at ||
      startedSource?.createdAt ||
      undefined,
  };
}

function safeMarkdownUrl(url) {
  const value = String(url || "").trim();
  if (/^(https?:|mailto:|tel:)/i.test(value)) return value;
  if (/^(\/|\.{1,2}\/|#)/.test(value)) return value;
  return value.includes(":") ? "" : value;
}

function normalizeCourseStatus(status) {
  return String(status || "")
    .trim()
    .toLowerCase();
}

function isDraftCourseStatus(status) {
  return normalizeCourseStatus(status) === "draft";
}

function isGenerationCourseStatus(status) {
  return ["in_generation", "generating", "queued"].includes(
    normalizeCourseStatus(status),
  );
}

function getStatusErrorMessage(error) {
  if (error?.status === 401) return "Сессия истекла. Войдите заново.";
  if (error?.status === 403) {
    return "Недостаточно прав для проверки статуса генерации курса.";
  }
  if (Number(error?.status) >= 400 && Number(error?.status) < 500) {
    return "Не удалось проверить статус генерации курса.";
  }
  if (Number(error?.status) >= 500) {
    return "Не удалось сгенерировать курс из-за ошибки сервера. Попробуйте позже.";
  }
  return "Не удалось проверить статус генерации курса. Проверьте соединение и попробуйте позже.";
}

export default function CreatorChatView() {
  const [courseId, setCourseId] = useState(createCourseId);
  const conversationKey = useMemo(
    () => createAgentConversationKey("interviewer", courseId),
    [courseId],
  );
  const conversation = useAgentStore(
    (state) => state.conversations[conversationKey],
  );
  const initializeConversation = useAgentStore(
    (state) => state.initializeConversation,
  );
  const appendAgentMessage = useAgentStore((state) => state.appendMessage);
  const sendAgentMessage = useAgentStore((state) => state.sendMessage);
  const clearConversation = useAgentStore((state) => state.clearConversation);
  const cancelRequest = useAgentStore((state) => state.cancelRequest);
  const setConversationChatId = useAgentStore((state) => state.setChatId);
  const storeGeneration = useAgentStore(
    (state) => state.generations[conversationKey],
  );
  const setGeneration = useAgentStore((state) => state.setGeneration);
  const resetGeneration = useAgentStore((state) => state.resetGeneration);
  const defaultGeneration = useMemo(createInitialGenerationState, []);
  const generation = storeGeneration || defaultGeneration;
  const messages = conversation?.messages || [];
  const isThinking = conversation?.status === "loading";
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [inputValue, setInputValue] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const hasGenerationStarted = generation.hasStarted;
  const isGenerating = generation.isGenerating;
  const generationProgress = generation.progress;
  const generationStatus = generation.status;
  const [fileUploadError, setFileUploadError] = useState("");
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);

  const fileInputRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const pollingTimerRef = useRef(null);
  const progressTimerRef = useRef(null);
  const statusRequestControllerRef = useRef(null);
  const statusRequestInFlightRef = useRef(false);
  const hasReceivedGenerationStatusRef = useRef(false);

  const requiredQuestionIds = [
    "title",
    "goal",
    "duration",
    "format",
    "level",
    "audience",
    "materials",
  ];
  const answeredRequiredCount = requiredQuestionIds.filter(
    (id) => (answers[id] || "").trim().length > 0,
  ).length;
  const briefingPercent = useMemo(
    () =>
      Math.round((answeredRequiredCount / requiredQuestionIds.length) * 100),
    [answeredRequiredCount],
  );

  const completionPercent = hasGenerationStarted
    ? generationProgress
    : briefingPercent;
  const isGenerationComplete =
    hasGenerationStarted && !isGenerating && generationProgress >= 100;
  const currentQuestion = intakeQuestions[stepIndex] || null;

  const updateGeneration = useCallback(
    (patch) => setGeneration(conversationKey, patch),
    [conversationKey, setGeneration],
  );

  const pushAssistantMessage = useCallback(
    (text) => {
      appendAgentMessage(conversationKey, "assistant", text);
    },
    [appendAgentMessage, conversationKey],
  );

  useEffect(() => {
    initializeConversation({
      key: conversationKey,
      agent: "interviewer",
      courseId,
    });
    return () => cancelRequest(conversationKey);
  }, [cancelRequest, conversationKey, courseId, initializeConversation]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isThinking]);

  const stopGenerationTimers = useCallback(() => {
    if (pollingTimerRef.current) {
      window.clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    statusRequestControllerRef.current?.abort();
    statusRequestControllerRef.current = null;
    statusRequestInFlightRef.current = false;
  }, []);

  const finishGeneration = useCallback(
    (status = "draft") => {
      stopGenerationTimers();
      clearGenerationState(courseId);
      updateGeneration({
        isGenerating: false,
        hasStarted: true,
        courseStatus: normalizeCourseStatus(status),
        progress: 100,
        error: "",
        status:
          "Курс сгенерирован! Он находится в профиле в разделе «Мои курсы».",
      });
      pushAssistantMessage(
        "Курс сгенерирован! Он находится в профиле в разделе «Мои курсы».",
      );
    },
    [courseId, pushAssistantMessage, stopGenerationTimers, updateGeneration],
  );

  const startProgressSimulation = useCallback(
    (startedAt) => {
      if (progressTimerRef.current) {
        window.clearInterval(progressTimerRef.current);
      }
      const tick = () => {
        const nextProgress = estimateProgress(startedAt);
        updateGeneration((current) => ({
          progress: Math.max(current.progress, nextProgress),
        }));
      };
      tick();
      progressTimerRef.current = window.setInterval(tick, PROGRESS_TICK_MS);
    },
    [updateGeneration],
  );

  const checkStatusOnce = useCallback(async () => {
    if (statusRequestInFlightRef.current) return false;

    const currentGeneration = useAgentStore
      .getState()
      .getGeneration(conversationKey);
    const statusLookupId = currentGeneration.generatedCourseId;
    if (!statusLookupId) {
      stopGenerationTimers();
      clearGenerationState(courseId);
      updateGeneration({
        isGenerating: false,
        error: "Не удалось проверить статус генерации курса.",
        status: "Не удалось проверить статус генерации курса.",
      });
      pushAssistantMessage("Не удалось проверить статус генерации курса.");
      return true;
    }

    statusRequestInFlightRef.current = true;
    const controller = new AbortController();
    statusRequestControllerRef.current = controller;

    try {
      const { status } = await fetchCourseStatus(statusLookupId, {
        signal: controller.signal,
      });
      const normalizedStatus = normalizeCourseStatus(status);

      if (isGenerationCourseStatus(normalizedStatus)) {
        hasReceivedGenerationStatusRef.current = true;
        updateGeneration({
          courseStatus: normalizedStatus,
          error: "",
          status: "Курс генерируется. Мы сообщим, когда он будет готов.",
        });
        return false;
      }
      if (isDraftCourseStatus(normalizedStatus)) {
        hasReceivedGenerationStatusRef.current = true;
        finishGeneration(normalizedStatus);
        return true;
      }
      updateGeneration({
        courseStatus: normalizedStatus,
        status: "Курс генерируется. Мы сообщим, когда он будет готов.",
      });
      return false;
    } catch (error) {
      if (controller.signal.aborted) return true;

      if (error?.status === NOT_FOUND_STATUS) {
        const started = Date.parse(currentGeneration.startedAt || "");
        const elapsed = Number.isFinite(started) ? Date.now() - started : 0;
        const shouldKeepPolling =
          !hasReceivedGenerationStatusRef.current &&
          elapsed < COURSE_GENERATION_NOT_FOUND_GRACE_MS;

        if (shouldKeepPolling) {
          updateGeneration({
            courseStatus: "not_found",
            error: "",
            status:
              "Задача генерации ещё подготавливается. Мы сообщим, когда курс будет готов.",
          });
          return false;
        }

        stopGenerationTimers();
        clearGenerationState(courseId);
        updateGeneration({
          isGenerating: false,
          hasStarted: false,
          taskId: null,
          generatedCourseId: null,
          courseStatus: "not_found",
          progress: 0,
          startedAt: null,
          error: "Не удалось сгенерировать курс.",
          status: "Не удалось сгенерировать курс.",
        });
        pushAssistantMessage("Не удалось сгенерировать курс.");
        return true;
      }

      console.error("Не удалось получить статус генерации курса", error);
      const errorMessage = getStatusErrorMessage(error);
      const shouldStopPolling = true;

      updateGeneration({
        isGenerating: !shouldStopPolling,
        error: errorMessage,
        status: errorMessage,
      });

      if (shouldStopPolling) {
        stopGenerationTimers();
        clearGenerationState(courseId);
        pushAssistantMessage(errorMessage);
        return true;
      }

      return false;
    } finally {
      if (statusRequestControllerRef.current === controller) {
        statusRequestControllerRef.current = null;
      }
      statusRequestInFlightRef.current = false;
    }
  }, [
    conversationKey,
    courseId,
    finishGeneration,
    pushAssistantMessage,
    stopGenerationTimers,
    updateGeneration,
  ]);

  const startStatusPolling = useCallback(async () => {
    if (pollingTimerRef.current) {
      window.clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    const finished = await checkStatusOnce();
    if (finished) return;
    pollingTimerRef.current = window.setInterval(
      checkStatusOnce,
      COURSE_GENERATION_POLLING_INTERVAL_MS,
    );
  }, [checkStatusOnce]);

  const beginGeneration = useCallback(
    ({
      taskId: nextTaskId,
      courseId: nextGeneratedCourseId,
      chatId: nextChatId,
      startedAt = new Date().toISOString(),
    }) => {
      hasReceivedGenerationStatusRef.current = false;
      const savedGeneratedCourseId = useAgentStore
        .getState()
        .getGeneration(conversationKey).generatedCourseId;
      const generationCourseId =
        nextGeneratedCourseId || savedGeneratedCourseId;
      updateGeneration({
        taskId: nextTaskId || null,
        generatedCourseId: generationCourseId || null,
        startedAt,
        hasStarted: true,
        isGenerating: true,
        courseStatus: "in_generation",
        progress: estimateProgress(startedAt),
        status: "Курс генерируется. Это может занять несколько минут.",
        error: "",
      });
      writeGenerationState({
        courseId,
        chatId: nextChatId || conversation?.chatId || null,
        taskId: nextTaskId || null,
        generatedCourseId: generationCourseId || null,
        generationStartedAt: startedAt,
        status: "in_generation",
      });
      startProgressSimulation(startedAt);
      startStatusPolling();
    },
    [
      conversation?.chatId,
      conversationKey,
      courseId,
      startProgressSimulation,
      startStatusPolling,
      updateGeneration,
    ],
  );

  const getFileValidationError = (file) => {
    if (!file) return "Файл не выбран.";
    if (file.size > DOCUMENT_MAX_SIZE_BYTES) {
      return "Размер файла не должен превышать 30 МБ.";
    }
    if (!DOCUMENT_ALLOWED_EXTENSION.test(file.name || "")) {
      return `Поддерживаются файлы ${DOCUMENT_ALLOWED_EXTENSIONS_LABEL}.`;
    }
    return "";
  };

  const uploadAllFiles = async () => {
    if (uploadedFiles.length === 0) {
      return true;
    }

    const validationErrors = uploadedFiles
      .map((uploadedFile) => ({
        name: uploadedFile.name,
        error: getFileValidationError(uploadedFile.file),
      }))
      .filter((item) => item.error);

    if (validationErrors.length > 0) {
      setFileUploadError(
        validationErrors
          .map((item) => `${item.name}: ${item.error}`)
          .join("\n"),
      );
      return false;
    }

    setIsUploadingFiles(true);
    setFileUploadError("");
    updateGeneration({ status: "Загружаю материалы в базу знаний..." });

    const results = await Promise.allSettled(
      uploadedFiles.map((uploadedFile) => saveDocument(uploadedFile.file)),
    );
    const failedUploads = results
      .map((result, index) => ({ result, file: uploadedFiles[index] }))
      .filter(({ result }) => result.status === "rejected")
      .map(({ result, file }) => {
        const error = result.reason;
        const reason =
          error?.userMessage ||
          error?.message ||
          (Number(error?.status) >= 500
            ? "Ошибка сервера при загрузке файла. Попробуйте ещё раз."
            : "Не удалось загрузить файл.");
        return `${file.name}: ${reason}`;
      });

    setIsUploadingFiles(false);

    if (failedUploads.length > 0) {
      setFileUploadError(failedUploads.join("\n"));
      return false;
    }

    return true;
  };

  useEffect(
    () => () => {
      stopGenerationTimers();
    },
    [stopGenerationTimers],
  );

  useEffect(() => {
    const savedGeneration = readGenerationState(courseId);
    if (!savedGeneration) return;

    setConversationChatId(conversationKey, savedGeneration.chatId || null);
    updateGeneration({
      taskId: savedGeneration.taskId || null,
      generatedCourseId: savedGeneration.generatedCourseId || null,
      startedAt: savedGeneration.generationStartedAt || null,
      hasStarted: true,
      isGenerating: true,
      courseStatus: "in_generation",
      progress: estimateProgress(savedGeneration.generationStartedAt),
      status: "Генерация курса продолжается.",
      error: "",
    });
    startProgressSimulation(savedGeneration.generationStartedAt);
    startStatusPolling();
  }, [
    conversationKey,
    courseId,
    setConversationChatId,
    startProgressSimulation,
    startStatusPolling,
    updateGeneration,
  ]);

  const submitMessage = async () => {
    const text = inputValue.trim();
    const hasFiles = uploadedFiles.length > 0;

    if (
      (!text && !hasFiles) ||
      isThinking ||
      isGenerating ||
      isUploadingFiles
    ) {
      return;
    }

    if (fileUploadError && !hasFiles) {
      return;
    }

    const targetQuestion = intakeQuestions[stepIndex] || null;
    const messageText = text || "Файлы прикреплены";

    if (hasFiles) {
      const filesOk = await uploadAllFiles();
      if (!filesOk) return;
    }

    if (targetQuestion && text) {
      setAnswers((prev) => ({
        ...prev,
        [targetQuestion.id]: text,
      }));
    }

    if (hasFiles) {
      setUploadedFiles([]);
    }

    setInputValue("");
    try {
      const response = await sendAgentMessage({
        key: conversationKey,
        agent: "interviewer",
        courseId,
        content: messageText,
        emptyResponseMessage: "",
      });
      if (!response) return;

      if (targetQuestion) {
        setStepIndex((current) =>
          Math.min(current + 1, intakeQuestions.length),
        );
      }
      const responseCourseId = extractCourseId(response);
      if (responseCourseId) {
        updateGeneration({ generatedCourseId: responseCourseId });
      }

      const generationResult = normalizeGenerationResponse(response);
      if (generationResult) {
        beginGeneration({
          taskId: generationResult.taskId,
          courseId: generationResult.courseId,
          chatId: response.chatId || conversation?.chatId,
          startedAt: generationResult.startedAt,
        });
      } else if (!String(response.content ?? "").trim()) {
        beginGeneration({
          taskId: null,
          courseId: null,
          chatId: response.chatId || conversation?.chatId,
        });
      }
    } catch {
      // Публичная ошибка отображается из Zustand-store без технических деталей.
    }
  };

  const pickFiles = (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) {
      return;
    }

    const remaining = MAX_FILES - uploadedFiles.length;
    const accepted = [];
    const existingFileKeys = new Set(
      uploadedFiles.map(
        (uploadedFile) =>
          `${uploadedFile.name}:${uploadedFile.file.size}:${uploadedFile.file.lastModified}`,
      ),
    );
    let skippedByLimit = false;
    let skippedBySize = false;
    let skippedDuplicate = false;

    for (const file of files) {
      if (accepted.length >= remaining) {
        skippedByLimit = true;
        continue;
      }
      const fileKey = `${file.name}:${file.size}:${file.lastModified}`;
      if (existingFileKeys.has(fileKey)) {
        skippedDuplicate = true;
        continue;
      }
      if (file.size > DOCUMENT_MAX_SIZE_BYTES) {
        skippedBySize = true;
        continue;
      }
      if (!DOCUMENT_ALLOWED_EXTENSION.test(file.name || "")) {
        const message = `Поддерживаются файлы ${DOCUMENT_ALLOWED_EXTENSIONS_LABEL}.`;
        setFileUploadError(message);
        pushAssistantMessage(message);
        continue;
      }
      accepted.push(file);
      existingFileKeys.add(fileKey);
    }

    if (skippedByLimit) {
      pushAssistantMessage(
        `Можно прикрепить не более ${MAX_FILES} файлов. Лишние файлы не добавлены.`,
      );
    }
    if (skippedBySize) {
      const message = "Файл больше 30 МБ не поддерживается и не был добавлен.";
      setFileUploadError(message);
      pushAssistantMessage(message);
    }

    const nextFiles = accepted.map((file, index) => ({
      id: `${file.name}-${Date.now()}-${index}`,
      name: file.name,
      sizeKb: Math.max(1, Math.round(file.size / 1024)),
      file,
    }));

    if (skippedDuplicate) {
      pushAssistantMessage("Повторно выбранные файлы не добавлены.");
    }

    if (nextFiles.length > 0) {
      setFileUploadError("");
      setUploadedFiles((prev) => [...nextFiles, ...prev]);
      setAnswers((prev) => ({
        ...prev,
        materials:
          prev.materials && prev.materials.trim().length > 0
            ? prev.materials
            : "Файлы прикреплены",
      }));
    }
    event.target.value = "";
  };

  const clearChat = () => {
    stopGenerationTimers();
    clearGenerationState(courseId);
    clearConversation(conversationKey);
    initializeConversation({
      key: conversationKey,
      agent: "interviewer",
      courseId,
    });
    setStepIndex(0);
    setAnswers({});
    setInputValue("");
    setUploadedFiles([]);
    resetGeneration(conversationKey);
    hasReceivedGenerationStatusRef.current = false;
    setFileUploadError("");
    setIsUploadingFiles(false);
  };

  const startNewChat = () => {
    stopGenerationTimers();
    clearGenerationState(courseId);
    clearConversation(conversationKey);
    setStepIndex(0);
    setAnswers({});
    setInputValue("");
    setUploadedFiles([]);
    resetGeneration(conversationKey);
    hasReceivedGenerationStatusRef.current = false;
    setFileUploadError("");
    setIsUploadingFiles(false);
    setCourseId(createUuid());
  };

  return (
    <section className="creator-chat-shell">
      {hasGenerationStarted && (
        <article className="glass-card creator-chat-topbar">
          <div className="creator-chat-top-main">
            <span>Создание курса</span>
            <h3>ИИ собирает структуру программы</h3>
            <p>{generationStatus}</p>
          </div>

          <div className="creator-chat-top-stats">
            <div>
              <span>Готовность</span>
              <strong>{completionPercent}%</strong>
            </div>
          </div>

          <div className="creator-chat-top-track">
            <div style={{ width: `${completionPercent}%` }} />
          </div>
        </article>
      )}

      {isGenerating && (
        <div className="creator-chat-layout is-generating">
          <article className="glass-card creator-chat-main">
            <div className="creator-chat-main-head">
              <h4>Чат-конструктор</h4>
              <span>ИИ работает...</span>
            </div>

            <div
              className="creator-chat-messages"
              ref={messagesContainerRef}
              aria-live="polite"
              aria-busy="true"
            >
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`creator-chat-msg ${message.role === "user" ? "is-user" : "is-assistant"}`}
                >
                  {message.role === "assistant" ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      urlTransform={safeMarkdownUrl}
                    >
                      {message.text}
                    </ReactMarkdown>
                  ) : (
                    <p>{message.text}</p>
                  )}
                  {message.role === "user" && (
                    <span className="chat-message-status">✓ Отправлено</span>
                  )}
                </div>
              ))}

              <div className="creator-chat-msg is-assistant is-thinking">
                <span className="chat-thinking-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                <p>Курс генерируется. Можно оставить страницу открытой.</p>
              </div>
            </div>

            <div className="creator-chat-runtime">
              <h5>Генерация курса</h5>
              <p>{generationStatus}</p>
              <div className="creator-chat-runtime-bar">
                <div style={{ width: `${completionPercent}%` }} />
              </div>
            </div>
          </article>
        </div>
      )}

      {isGenerationComplete && (
        <div className="creator-chat-layout is-briefing">
          <article className="glass-card creator-chat-main">
            <div className="creator-chat-main-head">
              <h4>Чат-конструктор</h4>
              <span>Курс готов</span>
            </div>

            <div
              className="creator-chat-messages"
              ref={messagesContainerRef}
              aria-live="polite"
            >
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`creator-chat-msg ${message.role === "user" ? "is-user" : "is-assistant"}`}
                >
                  {message.role === "assistant" ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      urlTransform={safeMarkdownUrl}
                    >
                      {message.text}
                    </ReactMarkdown>
                  ) : (
                    <p>{message.text}</p>
                  )}
                  {message.role === "user" && (
                    <span className="chat-message-status">✓ Отправлено</span>
                  )}
                </div>
              ))}
            </div>

            <div className="creator-chat-actions creator-chat-new-actions">
              <span>
                Можно начать новый диалог для создания следующего курса.
              </span>
              <button
                type="button"
                className="btn btn-solid"
                onClick={startNewChat}
              >
                Новый чат
              </button>
            </div>
          </article>
        </div>
      )}

      {!isGenerating && !isGenerationComplete && (
        <div className="creator-chat-layout is-briefing">
          <article className="glass-card creator-chat-main">
            <div className="creator-chat-main-head">
              <h4>Чат-конструктор</h4>
              <span>
                {isUploadingFiles
                  ? "Загружаю файлы..."
                  : isGenerating
                    ? "ИИ работает..."
                    : "Диалог активен"}
              </span>
            </div>

            <div
              className="creator-chat-messages"
              ref={messagesContainerRef}
              aria-live="polite"
              aria-busy={isThinking}
            >
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`creator-chat-msg ${message.role === "user" ? "is-user" : "is-assistant"}`}
                >
                  {message.role === "assistant" ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      urlTransform={safeMarkdownUrl}
                    >
                      {message.text}
                    </ReactMarkdown>
                  ) : (
                    <p>{message.text}</p>
                  )}
                  {message.role === "user" && (
                    <span className="chat-message-status">✓ Отправлено</span>
                  )}
                </div>
              ))}

              {isThinking && (
                <div className="creator-chat-msg is-assistant is-thinking">
                  <span className="chat-thinking-dots" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <p>Сообщение получено — думаю над следующим уточнением…</p>
                </div>
              )}
              {conversation?.error && (
                <p className="lesson-ai-error" role="alert">
                  {conversation.error}
                </p>
              )}
            </div>

            <div className="creator-chat-composer-wrap">
              <input
                ref={fileInputRef}
                type="file"
                className="knowledge-file-input"
                multiple
                accept=".pdf,.docx,.pptx,.xlsx,.md,.html,.txt,.json"
                onChange={pickFiles}
                disabled={isGenerating || isUploadingFiles}
              />
              <div className="creator-chat-composer">
                <button
                  type="button"
                  className="creator-chat-plus"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isGenerating || isUploadingFiles}
                  title="Загрузить файл"
                  aria-label="Загрузить файл"
                >
                  +
                </button>

                <textarea
                  placeholder={
                    currentQuestion?.placeholder || "Напишите сообщение для ИИ"
                  }
                  value={inputValue}
                  onChange={(event) => {
                    setInputValue(event.target.value);
                    if (fileUploadError && uploadedFiles.length === 0) {
                      setFileUploadError("");
                    }
                  }}
                  onKeyDown={(event) => {
                    if (event.nativeEvent.isComposing) {
                      return;
                    }

                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      submitMessage();
                    }
                  }}
                  maxLength={10_000}
                  disabled={isGenerating || isUploadingFiles}
                />

                <button
                  type="button"
                  className="btn btn-solid creator-chat-send-btn"
                  onClick={submitMessage}
                  disabled={
                    isGenerating ||
                    isUploadingFiles ||
                    isThinking ||
                    (Boolean(fileUploadError) && uploadedFiles.length === 0) ||
                    (!inputValue.trim() && uploadedFiles.length === 0)
                  }
                >
                  {isUploadingFiles
                    ? "Загружаю файлы..."
                    : isThinking
                      ? "Отправлено"
                      : "Отправить"}
                </button>
              </div>

              {uploadedFiles.length > 0 && (
                <ul className="knowledge-files-list">
                  {uploadedFiles.map((file) => (
                    <li key={file.id}>
                      {file.name} • {file.sizeKb} КБ
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {fileUploadError && (
              <p
                className="lesson-ai-error creator-chat-file-error"
                role="alert"
              >
                {fileUploadError}
              </p>
            )}

            <div className="creator-chat-actions">
              <span>
                Файлов прикреплено: {uploadedFiles.length} • Enter для отправки,
                Shift + Enter для новой строки
              </span>
              <div className="creator-chat-actions-buttons">
                {fileUploadError && (
                  <button
                    type="button"
                    className="btn btn-solid"
                    onClick={submitMessage}
                    disabled={
                      isUploadingFiles ||
                      isThinking ||
                      isGenerating ||
                      uploadedFiles.length === 0
                    }
                  >
                    {isUploadingFiles ? "Загружаю..." : "Повторить загрузку"}
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={clearChat}
                >
                  Очистить чат
                </button>
              </div>
            </div>
          </article>
        </div>
      )}
    </section>
  );
}
