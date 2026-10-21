import { useEffect, useMemo, useRef, useState } from "react";
import AppModal from "../ui/AppModal";
import FloatingWindow from "../ui/FloatingWindow";
import ConfirmDialog from "../ui/ConfirmDialog";
import AgentMarkdown from "./AgentMarkdown";
import { autosizeTextarea } from "../../utils/autosizeTextarea";
import { isAgentMockEnabled } from "../../services/agentMockHook";
import {
  CONFIRM_LAUNCH_MESSAGE,
  extractTaskId,
  getLastAssistantMessage,
  getResponseText,
  isAwaitingLaunchConfirmation,
  looksLikeLaunchConfirmation,
} from "./agentChatUtils";
import {
  createAgentConversationKey,
  useAgentStore,
} from "../../stores/agentStore";
import {
  generationJobKey,
  useGenerationJobsStore,
} from "../../stores/generationJobsStore";

const TEXTS = {
  module: {
    agent: "module_interviewer",
    eyebrow: "ИИ-генерация модуля",
    title: "Новый модуль с ИИ",
    intro:
      "Расскажите, какой модуль нужен: тема, для кого он и что студент должен уметь после него. Агент задаст пару уточняющих вопросов, покажет структуру и стоимость и попросит подтвердить запуск.",
    placeholder:
      "Например: модуль про расчёт отпускных для бухгалтеров-новичков",
    started: "Генерация модуля запущена.",
    confirmTitle: "Запустить генерацию модуля?",
    running: (job) =>
      job.resultId
        ? `Модуль «${job.resultTitle || "без названия"}» создаётся. Готово уроков: ${job.lessonsCount}.`
        : "Модуль генерируется. Это может занять несколько минут — окно можно закрыть.",
    done: (job) =>
      `Модуль «${job.resultTitle || "без названия"}» готов: ${job.lessonsCount} урок(ов).`,
    open: "Открыть модуль",
    another: "Сгенерировать ещё модуль",
    anotherHint:
      "Новый модуль встанет сразу после этого. Другое место можно выбрать в списке модулей — кнопка «Сгенерировать модуль здесь».",
  },
  lesson: {
    agent: "lesson_interviewer",
    eyebrow: "ИИ-генерация урока",
    title: "Новый урок с ИИ",
    intro:
      "Опишите урок: какую тему он раскрывает, что студент уже знает и чему должен научиться. Агент уточнит детали, покажет структуру и попросит подтвердить запуск.",
    placeholder: "Например: урок о том, как считать НДФЛ с премии",
    started: "Генерация урока запущена.",
    confirmTitle: "Запустить генерацию урока?",
    running: () =>
      "Урок генерируется. Это может занять несколько минут — окно можно закрыть.",
    done: (job) => `Урок «${job.resultTitle || "без названия"}» готов.`,
    open: "Открыть урок",
    another: "Сгенерировать ещё урок",
    anotherHint:
      "Новый урок встанет сразу после этого. Другое место можно выбрать в списке уроков — кнопка «Сгенерировать урок здесь».",
  },
};

const conversationKeyFor = (kind, courseId, moduleId = "") =>
  createAgentConversationKey(
    (TEXTS[kind] || TEXTS.module).agent,
    courseId,
    kind === "lesson" ? moduleId : "new-module",
  );

const jobKeyFor = (kind, courseId, moduleId = "") =>
  generationJobKey(kind, courseId, kind === "lesson" ? moduleId : "");

/**
 * Начинает генерацию заново: удаляет переписку (следующий запрос уйдёт с новым chat_id)
 * и завершённую или упавшую генерацию. Окно чата при этом остаётся открытым.
 */
export function resetAgentInterview({ kind, courseId, moduleId = "" }) {
  const key = conversationKeyFor(kind, courseId, moduleId);
  const agentState = useAgentStore.getState();
  agentState.cancelRequest(key);
  agentState.clearConversation(key);
  useGenerationJobsStore
    .getState()
    .removeJob(jobKeyFor(kind, courseId, moduleId));
}

/**
 * Диалог с ИИ-интервьюером модуля или урока.
 * chat_id хранится в agentStore (вместе с историей) и передаётся повторно,
 * пока пользователь не начнёт новый диалог.
 */
export default function AgentInterviewDialog({
  open,
  onClose,
  kind,
  courseId,
  moduleId = "",
  order,
  knownIds = [],
  contextTitle = "",
  onOpenResult,
  // Вызывается по кнопке «Сгенерировать ещё»: родитель выбирает место для следующего.
  onStartAnother,
  // "modal" — модальное окно, "floating" — плавающее окно, которое можно
  // перетаскивать и растягивать, не закрывая доступ к редактору.
  variant = "modal",
}) {
  const texts = TEXTS[kind] || TEXTS.module;
  const conversationKey = useMemo(
    () => conversationKeyFor(kind, courseId, moduleId),
    [courseId, kind, moduleId],
  );
  const jobKey = jobKeyFor(kind, courseId, moduleId);

  const conversation = useAgentStore(
    (state) => state.conversations[conversationKey],
  );
  const initializeConversation = useAgentStore(
    (state) => state.initializeConversation,
  );
  const sendAgentMessage = useAgentStore((state) => state.sendMessage);
  const appendMessage = useAgentStore((state) => state.appendMessage);
  const removeLastMessage = useAgentStore((state) => state.removeLastMessage);
  const clearConversation = useAgentStore((state) => state.clearConversation);
  const cancelRequest = useAgentStore((state) => state.cancelRequest);
  const job = useGenerationJobsStore((state) => state.jobs[jobKey] || null);
  const startJob = useGenerationJobsStore((state) => state.startJob);
  const removeJob = useGenerationJobsStore((state) => state.removeJob);

  const [input, setInput] = useState("");
  const [lastSent, setLastSent] = useState("");
  const [confirmText, setConfirmText] = useState(null);
  const [isResetOpen, setIsResetOpen] = useState(false);
  const messagesRef = useRef(null);
  const inputRef = useRef(null);
  const isFloating = variant === "floating";

  const messages = conversation?.messages || [];
  const isThinking = conversation?.status === "loading";
  const error = conversation?.status === "error" ? conversation.error : "";
  const isRunning = job?.status === "running";
  const isDone = job?.status === "done";
  const isFailed = job?.status === "error";
  const awaitingConfirmation =
    !job && !isThinking && isAwaitingLaunchConfirmation(messages);
  const lastAssistant = getLastAssistantMessage(messages);
  const canWrite =
    Boolean(courseId) && (kind !== "lesson" || Boolean(moduleId));

  useEffect(() => {
    if (!open || !courseId) return;
    initializeConversation({
      key: conversationKey,
      agent: texts.agent,
      courseId,
    });
  }, [conversationKey, courseId, initializeConversation, open, texts.agent]);

  useEffect(() => {
    const container = messagesRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages.length, isThinking, open, job?.status]);

  useEffect(() => {
    if (!open || !isFloating) return;
    window.requestAnimationFrame(() =>
      inputRef.current?.focus({ preventScroll: true }),
    );
  }, [isFloating, open]);

  useEffect(() => {
    autosizeTextarea(inputRef.current, 180);
  }, [input, open]);

  const send = async (text) => {
    const content = String(text || "").trim();
    if (!content || isThinking || job || !canWrite) return;
    setLastSent(content);
    setInput("");
    try {
      const response = await sendAgentMessage({
        key: conversationKey,
        agent: texts.agent,
        courseId,
        content,
        editorPayload: {
          order,
          ...(kind === "lesson" ? { module_id: moduleId } : {}),
        },
        emptyResponseMessage:
          "Агент вернул пустой ответ. Попробуйте переформулировать.",
        responseDisplayMessage: (result) =>
          getResponseText(result, texts.started),
      });
      if (!response) return;
      const taskId = extractTaskId(response);
      if (taskId) {
        startJob({
          key: jobKey,
          kind,
          courseId,
          moduleId,
          order,
          taskId,
          chatKey: conversationKey,
          knownIds,
        });
      }
    } catch {
      // Ошибка показывается из agentStore; текст можно отправить повторно.
    }
  };

  const submit = (event) => {
    event?.preventDefault?.();
    const text = input.trim();
    if (!text) return;
    // Согласие на запуск сначала показываем в окне подтверждения.
    if (awaitingConfirmation && looksLikeLaunchConfirmation(text)) {
      setConfirmText(text);
      return;
    }
    send(text);
  };

  const retry = () => {
    if (!lastSent) return;
    removeLastMessage(conversationKey, "user");
    send(lastSent);
  };

  const resetDialog = () => {
    cancelRequest(conversationKey);
    clearConversation(conversationKey);
    removeJob(jobKey);
    initializeConversation({
      key: conversationKey,
      agent: texts.agent,
      courseId,
    });
    setInput("");
    setLastSent("");
    setIsResetOpen(false);
  };

  // Готовый результат остаётся в редакторе, а чат сразу готов к следующей генерации.
  const startAnother = () => {
    const result = job;
    resetDialog();
    onStartAnother?.(result);
  };

  const finishAndOpen = () => {
    if (!job) return;
    const result = job;
    // Диалог завершён: следующий запуск начнётся с нового chat_id.
    clearConversation(conversationKey);
    removeJob(jobKey);
    onOpenResult?.(result);
  };

  const chatBody = (
    <div className="agent-chat">
      {isAgentMockEnabled() ? (
        <p className="agent-mock-badge">
          Демо-режим: ответы ИИ имитируются, модель не вызывается. Модуль и
          уроки создаются настоящими запросами к backend.
        </p>
      ) : null}
      <div className="agent-chat-messages" ref={messagesRef} aria-live="polite">
        {messages.length === 0 ? (
          <p className="agent-chat-empty">{texts.intro}</p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`agent-chat-message is-${message.role}`}
            >
              {message.role === "assistant" ? (
                <AgentMarkdown>{message.text}</AgentMarkdown>
              ) : (
                message.text
              )}
            </div>
          ))
        )}
        {isThinking ? (
          <span className="agent-chat-thinking">Агент думает...</span>
        ) : null}
      </div>

      {error ? (
        <div className="agent-chat-status is-error" role="alert">
          <span>{error}</span>
          {lastSent ? (
            <div>
              <button type="button" className="btn btn-outline" onClick={retry}>
                Отправить ещё раз
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {awaitingConfirmation ? (
        <div className="agent-chat-launch">
          <span>
            Агент подготовил описание и цели. Проверьте их перед запуском —
            после запуска генерацию нельзя отменить.
          </span>
          <button
            type="button"
            className="btn btn-solid"
            onClick={() => setConfirmText(CONFIRM_LAUNCH_MESSAGE)}
          >
            Проверить и запустить
          </button>
        </div>
      ) : null}

      {isRunning ? (
        <div className="agent-chat-status" role="status">
          <strong>{texts.running(job)}</strong>
          <span>Новые данные появятся в редакторе автоматически.</span>
        </div>
      ) : null}
      {isDone ? (
        <div className="agent-chat-status is-done" role="status">
          <strong>{texts.done(job)}</strong>
          <span>{texts.anotherHint}</span>
          <div>
            <button
              type="button"
              className="btn btn-solid"
              onClick={startAnother}
            >
              {texts.another}
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={finishAndOpen}
            >
              {texts.open}
            </button>
          </div>
        </div>
      ) : null}
      {isFailed ? (
        <div className="agent-chat-status is-error" role="alert">
          <span>{job.error || "Генерация не завершилась."}</span>
          <div>
            <button
              type="button"
              className="btn btn-outline"
              onClick={resetDialog}
            >
              Начать заново
            </button>
          </div>
        </div>
      ) : null}

      {!job ? (
        <form className="agent-chat-form" onSubmit={submit}>
          <textarea
            ref={(element) => {
              inputRef.current = element;
              autosizeTextarea(element, 180);
            }}
            rows={1}
            value={input}
            placeholder={texts.placeholder}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            disabled={isThinking || !canWrite}
            maxLength={10000}
            aria-label="Сообщение агенту"
          />
          <button
            type="submit"
            className="btn btn-solid"
            disabled={isThinking || !input.trim() || !canWrite}
          >
            {isThinking ? "Ждём ответ..." : "Отправить"}
          </button>
        </form>
      ) : null}
    </div>
  );

  const resetButton =
    messages.length > 0 || job ? (
      <button
        type="button"
        className="btn btn-outline"
        onClick={() => setIsResetOpen(true)}
        disabled={isThinking}
      >
        Начать новый диалог
      </button>
    ) : null;

  if (isFloating && !open) return null;

  return (
    <>
      {isFloating ? (
        <FloatingWindow
          open={open}
          onClose={onClose}
          eyebrow={texts.eyebrow}
          title={texts.title}
          subtitle={contextTitle}
          storageKey={`agent-${kind}`}
          defaultSize={{ width: 460, height: 620 }}
          headerActions={resetButton}
        >
          {chatBody}
        </FloatingWindow>
      ) : (
        <AppModal
          open={open}
          onClose={onClose}
          size="lg"
          eyebrow={texts.eyebrow}
          title={texts.title}
          description={contextTitle}
          footer={
            <>
              {resetButton}
              <button
                type="button"
                className="btn btn-outline"
                onClick={onClose}
              >
                Закрыть
              </button>
            </>
          }
        >
          {chatBody}
        </AppModal>
      )}

      <ConfirmDialog
        open={confirmText !== null}
        title={texts.confirmTitle}
        eyebrow="Проверьте перед запуском"
        description="Описание и цели обучения, которые подготовил агент. Если что-то не так — нажмите «Отмена» и напишите правки в чат."
        confirmLabel="Подтвердить и запустить"
        busyLabel="Отправляем..."
        size="lg"
        onCancel={() => setConfirmText(null)}
        onConfirm={async () => {
          const text = confirmText || CONFIRM_LAUNCH_MESSAGE;
          setConfirmText(null);
          await send(text);
        }}
      >
        <div className="agent-launch-summary">
          <AgentMarkdown>{lastAssistant?.text || ""}</AgentMarkdown>
        </div>
        <p className="app-modal-note">
          После подтверждения агент поставит генерацию в очередь. Готовый
          результат появится в редакторе — следить за ним можно в этом окне.
        </p>
      </ConfirmDialog>

      <ConfirmDialog
        open={isResetOpen}
        title="Начать новый диалог?"
        description={
          isRunning
            ? "Текущая переписка удалится. Уже запущенная генерация продолжится на сервере, но окно перестанет за ней следить."
            : "Текущая переписка с агентом удалится, следующий диалог начнётся с нуля."
        }
        confirmLabel="Начать заново"
        danger
        onCancel={() => setIsResetOpen(false)}
        onConfirm={resetDialog}
      />
    </>
  );
}
