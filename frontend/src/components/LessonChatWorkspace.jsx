import { useCallback, useEffect, useId, useRef, useState } from "react";
import LessonAiChat from "./LessonAiChat";

const COMPACT_QUERY = "(max-width: 1300px)";
const MIN_CHAT_WIDTH = 380;
const MIN_THEORY_WIDTH = 520;
const DEFAULT_CHAT_WIDTH = 420;
const RESIZE_STEP = 16;
const WIDE_RESIZE_STEP = 48;

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export default function LessonChatWorkspace({
  className = "",
  children,
  chatEnabled,
  chatAvailable,
  chatKey,
  chatProps,
}) {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [hasUnreadResponse, setHasUnreadResponse] = useState(false);
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH);
  const [widthBounds, setWidthBounds] = useState({
    min: MIN_CHAT_WIDTH,
    max: DEFAULT_CHAT_WIDTH,
  });
  const [isResizing, setIsResizing] = useState(false);
  const workspaceRef = useRef(null);
  const openButtonRef = useRef(null);
  const focusFrameRef = useRef(null);
  const focusChatOnOpenRef = useRef(false);
  const dragStartRef = useRef({ x: 0, width: DEFAULT_CHAT_WIDTH });
  const chatPanelId = useId();

  const updateWidthBounds = useCallback(() => {
    const workspace = workspaceRef.current;
    if (!workspace || window.matchMedia(COMPACT_QUERY).matches) return;

    const navigationWidth =
      workspace.querySelector(".course-nav-tree")?.getBoundingClientRect()
        .width || 0;
    const styles = window.getComputedStyle(workspace);
    const columnGap = Number.parseFloat(styles.columnGap) || 14;
    const splitterWidth = 12;
    const max = Math.max(
      MIN_CHAT_WIDTH,
      workspace.clientWidth -
        navigationWidth -
        MIN_THEORY_WIDTH -
        splitterWidth -
        columnGap * 3,
    );

    setWidthBounds({ min: MIN_CHAT_WIDTH, max });
    setChatWidth((current) => clamp(current, MIN_CHAT_WIDTH, max));
  }, []);

  useEffect(() => {
    setIsChatOpen(false);
    setHasUnreadResponse(false);
    setIsResizing(false);
  }, [chatKey]);

  useEffect(() => {
    if (!chatAvailable) {
      setIsChatOpen(false);
    }
  }, [chatAvailable]);

  useEffect(() => {
    if (!isChatOpen) return undefined;

    updateWidthBounds();
    window.addEventListener("resize", updateWidthBounds);

    const workspace = workspaceRef.current;
    const resizeObserver =
      workspace && "ResizeObserver" in window
        ? new ResizeObserver(updateWidthBounds)
        : null;
    resizeObserver?.observe(workspace);

    return () => {
      window.removeEventListener("resize", updateWidthBounds);
      resizeObserver?.disconnect();
    };
  }, [isChatOpen, updateWidthBounds]);

  useEffect(() => {
    if (!isResizing) return undefined;

    document.body.classList.add("is-resizing-lesson-chat");
    const handlePointerMove = (event) => {
      const delta = dragStartRef.current.x - event.clientX;
      setChatWidth(
        clamp(
          dragStartRef.current.width + delta,
          widthBounds.min,
          widthBounds.max,
        ),
      );
    };
    const stopResizing = () => setIsResizing(false);

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    window.addEventListener("pointercancel", stopResizing);
    window.addEventListener("blur", stopResizing);
    return () => {
      document.body.classList.remove("is-resizing-lesson-chat");
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
      window.removeEventListener("pointercancel", stopResizing);
      window.removeEventListener("blur", stopResizing);
    };
  }, [isResizing, widthBounds]);

  useEffect(
    () => () => {
      if (focusFrameRef.current) {
        cancelAnimationFrame(focusFrameRef.current);
      }
    },
    [],
  );

  const openChat = useCallback((event) => {
    focusChatOnOpenRef.current = event.detail === 0;
    setHasUnreadResponse(false);
    setIsChatOpen(true);
  }, []);
  const markResponseAsUnread = useCallback(() => {
    setHasUnreadResponse(true);
  }, []);
  const closeChat = useCallback(() => {
    setIsChatOpen(false);
    focusFrameRef.current = requestAnimationFrame(() =>
      openButtonRef.current?.focus(),
    );
  }, []);

  const resizeWithKeyboard = (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const step = event.shiftKey ? WIDE_RESIZE_STEP : RESIZE_STEP;
    const direction = event.key === "ArrowLeft" ? 1 : -1;
    setChatWidth((current) =>
      clamp(current + direction * step, widthBounds.min, widthBounds.max),
    );
  };

  return (
    <div
      ref={workspaceRef}
      className={`lesson-view-grid lesson-chat-workspace ${className} ${
        isChatOpen ? "has-lesson-chat" : ""
      } ${isResizing ? "is-resizing" : ""}`}
      style={{ "--lesson-chat-width": `${chatWidth}px` }}
    >
      {children}

      {chatEnabled && (
        <>
          {chatAvailable && !isChatOpen && (
            <button
              ref={openButtonRef}
              type="button"
              className={`lesson-chat-open-button ${
                hasUnreadResponse ? "has-unread-response" : ""
              }`}
              onClick={openChat}
              aria-haspopup="dialog"
              aria-controls={chatPanelId}
              aria-expanded="false"
              aria-label={
                hasUnreadResponse ? "Открыть новый ответ ИИ" : "Открыть ИИ-чат"
              }
            >
              <span className="lesson-chat-open-icon" aria-hidden="true">
                ✦
              </span>
              <span className="lesson-chat-open-label" aria-live="polite">
                {hasUnreadResponse ? "Ответ ИИ готов" : "Спросить ИИ"}
              </span>
              {hasUnreadResponse && (
                <span className="lesson-chat-unread-dot" aria-hidden="true" />
              )}
            </button>
          )}

          {isChatOpen && (
            <div
              className="lesson-chat-resizer"
              role="separator"
              tabIndex={0}
              aria-label="Изменить ширину ИИ-чата"
              aria-orientation="vertical"
              aria-valuemin={Math.round(widthBounds.min)}
              aria-valuemax={Math.round(widthBounds.max)}
              aria-valuenow={Math.round(chatWidth)}
              onPointerDown={(event) => {
                if (event.button !== 0) return;
                event.preventDefault();
                dragStartRef.current = { x: event.clientX, width: chatWidth };
                setIsResizing(true);
              }}
              onKeyDown={resizeWithKeyboard}
            >
              <span aria-hidden="true" />
            </div>
          )}

          <LessonAiChat
            key={chatKey}
            {...chatProps}
            panelId={chatPanelId}
            focusOnOpen={focusChatOnOpenRef.current}
            isOpen={isChatOpen}
            onClose={closeChat}
            onAssistantResponse={markResponseAsUnread}
          />
        </>
      )}
    </div>
  );
}
