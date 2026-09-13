import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  createAgentConversationKey,
  useAgentStore,
} from "../stores/agentStore";

const COMPACT_QUERY = "(max-width: 1300px)";
const QUICK_PROMPTS = [
  "Объяснить проще",
  "Привести пример",
  "Составить краткий конспект",
  "Помочь с практическим заданием",
];

function safeMarkdownUrl(url) {
  const value = String(url || "").trim();
  if (/^(https?:|mailto:|tel:)/i.test(value)) return value;
  if (/^(\/|\.{1,2}\/|#)/.test(value)) return value;
  return value.includes(":") ? "" : value;
}

export default function LessonAiChat({
  courseId,
  lessonId,
  lessonTitle,
  contentBlocks = [],
  onDownloadSummary,
  panelId,
  focusOnOpen = false,
  isOpen,
  onClose,
  onAssistantResponse,
}) {
  const [inputValue, setInputValue] = useState("");
  const [isCompact, setIsCompact] = useState(
    () => window.matchMedia(COMPACT_QUERY).matches,
  );
  const messagesRef = useRef(null);
  const panelRef = useRef(null);
  const closeButtonRef = useRef(null);
  const latestAssistantMessageRef = useRef(null);
  const didObserveMessagesRef = useRef(false);
  const conversationKey = useMemo(
    () => createAgentConversationKey("mentor", courseId, lessonId),
    [courseId, lessonId],
  );
  const conversation = useAgentStore(
    (state) => state.conversations[conversationKey],
  );
  const initializeConversation = useAgentStore(
    (state) => state.initializeConversation,
  );
  const sendAgentMessage = useAgentStore((state) => state.sendMessage);
  const cancelRequest = useAgentStore((state) => state.cancelRequest);
  const messages = conversation?.messages || [];
  const isSending = conversation?.status === "loading";

  useEffect(() => {
    initializeConversation({
      key: conversationKey,
      agent: "mentor",
      courseId,
    });
    return () => cancelRequest(conversationKey);
  }, [cancelRequest, conversationKey, courseId, initializeConversation]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(COMPACT_QUERY);
    const handleChange = (event) => setIsCompact(event.matches);
    setIsCompact(mediaQuery.matches);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    const latestAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");
    const latestAssistantMessageId = latestAssistantMessage?.id || null;

    if (!didObserveMessagesRef.current) {
      didObserveMessagesRef.current = true;
      latestAssistantMessageRef.current = latestAssistantMessageId;
      return;
    }

    if (
      latestAssistantMessageId &&
      latestAssistantMessageId !== latestAssistantMessageRef.current
    ) {
      latestAssistantMessageRef.current = latestAssistantMessageId;
      if (!isOpen) onAssistantResponse?.();
    }
  }, [isOpen, messages, onAssistantResponse]);

  useEffect(() => {
    const container = messagesRef.current;
    if (container && isOpen) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, isSending, isOpen]);

  useEffect(() => {
    if (isOpen && !isCompact && focusOnOpen) {
      closeButtonRef.current?.focus();
    }
  }, [focusOnOpen, isCompact, isOpen]);

  useEffect(() => {
    if (!isOpen || !isCompact) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = panelRef.current?.querySelectorAll(
        'button:not(:disabled), textarea:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isCompact, isOpen, onClose]);

  const sendMessage = async (value = inputValue) => {
    const prompt = value.trim();
    if (!prompt || isSending || !courseId) return;

    setInputValue("");
    try {
      await sendAgentMessage({
        key: conversationKey,
        agent: "mentor",
        courseId,
        content: prompt,
        contentBlocks,
      });
    } catch {
      // Публичная ошибка уже сохранена в store; технические детали не логируем.
    }
  };

  return (
    <>
      {isOpen && isCompact && (
        <button
          type="button"
          className="lesson-chat-backdrop"
          onClick={onClose}
          tabIndex={-1}
          aria-label="Закрыть ИИ-чат"
        />
      )}
      <aside
        ref={panelRef}
        id={panelId}
        className="lesson-page-ai-chat"
        aria-labelledby={`${panelId}-title`}
        role={isCompact ? "dialog" : "complementary"}
        aria-modal={isCompact ? "true" : undefined}
        hidden={!isOpen}
      >
        <div className="lesson-ai-editor-head">
          <div className="lesson-page-ai-chat-title">
            <span id={`${panelId}-title`}>ИИ-чат</span>
            <strong>
              {lessonTitle ? `По уроку: ${lessonTitle}` : "По материалам урока"}
            </strong>
          </div>
          <div className="lesson-page-ai-chat-head-actions">
            {onDownloadSummary && (
              <button
                type="button"
                className="lesson-page-ai-chat-download"
                onClick={onDownloadSummary}
                aria-label="Сохранить конспект урока в PDF"
                title="Сохранить конспект в PDF"
              >
                <span aria-hidden="true">⇩</span>
              </button>
            )}
            <button
              ref={closeButtonRef}
              type="button"
              className="lesson-page-ai-chat-toggle"
              onClick={onClose}
              aria-label={isCompact ? "Вернуться к уроку" : "Закрыть ИИ-чат"}
              title={isCompact ? "Вернуться к уроку" : "Закрыть чат"}
            >
              <span aria-hidden="true">×</span>
            </button>
          </div>
        </div>

        <div
          className="lesson-page-ai-chat-messages"
          ref={messagesRef}
          aria-live="polite"
          aria-busy={isSending}
        >
          {messages.length === 0 && !isSending && (
            <div className="lesson-chat-empty-state">
              <div>
                <span aria-hidden="true">✦</span>
                <h2>Чем помочь по этому уроку?</h2>
                <p>Спросите о сложном месте или выберите быстрый запрос.</p>
              </div>
              <div
                className="lesson-chat-quick-actions"
                aria-label="Быстрые запросы"
              >
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => sendMessage(prompt)}
                    disabled={isSending || !courseId}
                    aria-label={`${prompt} по текущему уроку`}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((message) => (
            <article
              key={message.id}
              className={`lesson-page-ai-chat-message is-${message.role}`}
            >
              <div className="lesson-chat-message-meta">
                <span className="lesson-chat-message-avatar" aria-hidden="true">
                  {message.role === "assistant" ? "✦" : "Вы"}
                </span>
                <strong>
                  {message.role === "assistant" ? "ИИ-помощник" : "Вы"}
                </strong>
              </div>
              <div className="lesson-chat-message-body">
                {message.role === "assistant" ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    urlTransform={safeMarkdownUrl}
                  >
                    {message.text}
                  </ReactMarkdown>
                ) : (
                  <span>{message.text}</span>
                )}
              </div>
              {message.role === "user" && (
                <span className="chat-message-status">✓ Отправлено</span>
              )}
            </article>
          ))}
          {isSending && (
            <article className="lesson-page-ai-chat-message is-assistant is-thinking">
              <div className="lesson-chat-message-meta">
                <span className="lesson-chat-message-avatar" aria-hidden="true">
                  ✦
                </span>
                <strong>ИИ-помощник</strong>
              </div>
              <div className="lesson-chat-message-body">
                <span className="chat-thinking-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                <span>Готовит ответ…</span>
              </div>
            </article>
          )}
          {conversation?.error && (
            <p className="lesson-ai-error" role="alert">
              {conversation.error}
            </p>
          )}
        </div>

        <div className="lesson-ai-composer lesson-page-ai-chat-composer">
          <textarea
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            maxLength={10_000}
            rows={2}
            placeholder={
              isSending ? "Дождитесь ответа ИИ" : "Напишите сообщение для ИИ"
            }
            disabled={!courseId}
            aria-label="Сообщение для ИИ"
            onKeyDown={(event) => {
              if (event.nativeEvent.isComposing) return;
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
              }
            }}
          />
          <button
            type="button"
            className="lesson-ai-send"
            onClick={() => sendMessage()}
            disabled={!inputValue.trim() || isSending || !courseId}
            aria-label={isSending ? "ИИ готовит ответ" : "Отправить сообщение"}
            title="Отправить"
          >
            ↑
          </button>
        </div>
      </aside>
    </>
  );
}
