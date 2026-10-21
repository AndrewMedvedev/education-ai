import { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getLocalStorage } from "../../utils/storage";
import "./floating-window.css";

const MARGIN = 12;
const MIN_VISIBLE = 120;
const MOBILE_QUERY = "(max-width: 720px)";

function readRect(storageKey) {
  if (!storageKey) return null;
  try {
    const value = JSON.parse(
      getLocalStorage()?.getItem(`floating-window:${storageKey}`) || "null",
    );
    return value && Number.isFinite(value.x) && Number.isFinite(value.w)
      ? value
      : null;
  } catch {
    return null;
  }
}

function writeRect(storageKey, rect) {
  if (!storageKey) return;
  try {
    getLocalStorage()?.setItem(
      `floating-window:${storageKey}`,
      JSON.stringify(rect),
    );
  } catch {
    // Позиция окна — удобство: без localStorage просто не запоминаем.
  }
}

function clampRect(rect, minSize) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const w = Math.min(Math.max(rect.w, minSize.width), vw - MARGIN * 2);
  const h = Math.min(Math.max(rect.h, minSize.height), vh - MARGIN * 2);
  // Окно можно утащить частично за край, но шапка всегда остаётся доступной.
  const x = Math.min(Math.max(rect.x, MIN_VISIBLE - w), vw - MIN_VISIBLE);
  const y = Math.min(Math.max(rect.y, MARGIN), vh - 56);
  return { x, y, w, h };
}

function defaultRect(defaultSize) {
  const w = Math.min(defaultSize.width, window.innerWidth - MARGIN * 2);
  const h = Math.min(defaultSize.height, window.innerHeight - MARGIN * 2);
  return {
    x: window.innerWidth - w - 24,
    y: Math.max(MARGIN, window.innerHeight - h - 24),
    w,
    h,
  };
}

/**
 * Плавающее окно: перетаскивается за шапку, растягивается за края и угол,
 * сворачивается в шапку. Положение и размер запоминаются по storageKey.
 * На узком экране открывается снизу на всю ширину без перетаскивания.
 */
export default function FloatingWindow({
  open,
  title,
  eyebrow = "",
  subtitle = "",
  onClose,
  storageKey = "",
  defaultSize = { width: 460, height: 600 },
  minSize = { width: 320, height: 260 },
  headerActions = null,
  className = "",
  children,
}) {
  const titleId = useId();
  const [rect, setRect] = useState(null);
  const [minimized, setMinimized] = useState(false);
  const [isMobile, setIsMobile] = useState(
    () =>
      typeof window !== "undefined" && window.matchMedia(MOBILE_QUERY).matches,
  );
  const gestureRef = useRef(null);
  const rectRef = useRef(null);
  rectRef.current = rect;

  useEffect(() => {
    if (!open) return;
    setRect(
      clampRect(readRect(storageKey) || defaultRect(defaultSize), minSize),
    );
    setMinimized(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, storageKey]);

  useEffect(() => {
    const media = window.matchMedia(MOBILE_QUERY);
    const onChange = () => setIsMobile(media.matches);
    media.addEventListener("change", onChange);
    const onResize = () =>
      setRect((current) => (current ? clampRect(current, minSize) : current));
    window.addEventListener("resize", onResize);
    return () => {
      media.removeEventListener("change", onChange);
      window.removeEventListener("resize", onResize);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startGesture = useCallback(
    (event, mode) => {
      if (isMobile || event.button !== 0 || !rectRef.current) return;
      if (
        mode === "move" &&
        event.target.closest("button, a, input, textarea")
      ) {
        return;
      }
      event.preventDefault();
      event.currentTarget.setPointerCapture?.(event.pointerId);
      gestureRef.current = {
        mode,
        startX: event.clientX,
        startY: event.clientY,
        start: rectRef.current,
      };
    },
    [isMobile],
  );

  const moveGesture = useCallback(
    (event) => {
      const gesture = gestureRef.current;
      if (!gesture) return;
      const dx = event.clientX - gesture.startX;
      const dy = event.clientY - gesture.startY;
      const { start, mode } = gesture;
      let next = { ...start };
      if (mode === "move") {
        next = { ...start, x: start.x + dx, y: start.y + dy };
      } else {
        if (mode.includes("e")) next.w = start.w + dx;
        if (mode.includes("s")) next.h = start.h + dy;
        if (mode.includes("w")) {
          next.w = start.w - dx;
          next.x = start.x + dx;
        }
      }
      const clamped = clampRect(next, minSize);
      // При растягивании влево фиксируем правый край окна.
      if (mode.includes("w") && clamped.w !== next.w) {
        clamped.x = start.x + start.w - clamped.w;
      }
      setRect(clamped);
    },
    [minSize],
  );

  const endGesture = useCallback(() => {
    if (!gestureRef.current) return;
    gestureRef.current = null;
    if (rectRef.current) writeRect(storageKey, rectRef.current);
  }, [storageKey]);

  if (!open || !rect) return null;

  const style = isMobile
    ? undefined
    : {
        left: rect.x,
        top: rect.y,
        width: rect.w,
        height: minimized ? "auto" : rect.h,
      };

  return createPortal(
    <section
      className={`floating-window ${minimized ? "is-minimized" : ""} ${isMobile ? "is-mobile" : ""} ${className}`.trim()}
      style={style}
      role="dialog"
      aria-modal="false"
      aria-labelledby={titleId}
      onPointerMove={moveGesture}
      onPointerUp={endGesture}
      onPointerCancel={endGesture}
    >
      <header
        className="floating-window-head"
        onPointerDown={(event) => startGesture(event, "move")}
        onDoubleClick={(event) => {
          if (!event.target.closest("button")) setMinimized((value) => !value);
        }}
        title={isMobile ? undefined : "Перетащите, чтобы переместить окно"}
      >
        <div className="floating-window-titles">
          {eyebrow ? (
            <span className="floating-window-eyebrow">{eyebrow}</span>
          ) : null}
          <h3 id={titleId}>{title}</h3>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <div className="floating-window-actions">
          {!minimized ? headerActions : null}
          <button
            type="button"
            className="floating-window-btn"
            onClick={() => setMinimized((value) => !value)}
            aria-label={minimized ? "Развернуть окно" : "Свернуть окно"}
            title={minimized ? "Развернуть" : "Свернуть"}
          >
            {minimized ? "▢" : "–"}
          </button>
          <button
            type="button"
            className="floating-window-btn"
            onClick={() => onClose?.()}
            aria-label="Закрыть окно"
            title="Закрыть"
          >
            ×
          </button>
        </div>
      </header>
      {!minimized ? (
        <div className="floating-window-body">{children}</div>
      ) : null}
      {!minimized && !isMobile ? (
        <>
          <span
            className="floating-window-resize is-e"
            onPointerDown={(event) => startGesture(event, "e")}
            aria-hidden="true"
          />
          <span
            className="floating-window-resize is-w"
            onPointerDown={(event) => startGesture(event, "w")}
            aria-hidden="true"
          />
          <span
            className="floating-window-resize is-s"
            onPointerDown={(event) => startGesture(event, "s")}
            aria-hidden="true"
          />
          <span
            className="floating-window-resize is-se"
            onPointerDown={(event) => startGesture(event, "se")}
            aria-hidden="true"
            title="Потяните, чтобы изменить размер"
          />
          <span
            className="floating-window-resize is-sw"
            onPointerDown={(event) => startGesture(event, "sw")}
            aria-hidden="true"
          />
        </>
      ) : null}
    </section>,
    // Внутрь .page, как и модальные окна: там действуют цвета и стили темы
    // (.page[data-theme="dark"] …) — иначе поле ввода в тёмной теме было нечитаемым.
    document.querySelector(".page") || document.body,
  );
}
