import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import MermaidDiagram from "./MermaidDiagram";

const MIN_SCALE = 0.25;
const MAX_SCALE = 8;
const MIN_LABEL_PX = 14;
const FIT_PADDING = 20;
const clamp = (value) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, value));

export default function DiagramPreviewModal({ chart, lessonId, blockId, onClose }) {
  const dialogRef = useRef(null);
  const viewportRef = useRef(null);
  const closeRef = useRef(null);
  const sizeRef = useRef(null);
  const viewRef = useRef({ scale: 1, x: 0, y: 0 });
  const fitRef = useRef(1);
  const pointers = useRef(new Map());
  const gesture = useRef(null);
  const lastTap = useRef(null);
  const backdropPressed = useRef(false);
  const userAdjusted = useRef(false);
  const [view, setView] = useState(viewRef.current);
  const [size, setSize] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [isDark, setIsDark] = useState(() =>
    typeof document !== "undefined" && Boolean(document.querySelector('.page[data-theme="dark"]')),
  );
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const changeView = useCallback((next, fromFit = false) => {
    userAdjusted.current = !fromFit;
    viewRef.current = next;
    setView(next);
  }, []);

  const fit = useCallback((whole) => {
    const viewport = viewportRef.current;
    const diagram = sizeRef.current;
    if (!viewport || !diagram) return;
    const availableWidth = Math.max(1, viewport.clientWidth - FIT_PADDING * 2);
    const availableHeight = Math.max(1, viewport.clientHeight - FIT_PADDING * 2);
    const fitScale = Math.min(availableWidth / diagram.width, availableHeight / diagram.height);
    // Подписи при открытии не мельче 14px: если целиком схема не влезает с читаемым
    // текстом, открываем крупнее и даём панорамировать.
    const readableScale = Math.min(2, MIN_LABEL_PX / Math.max(1, diagram.fontSize));
    // whole === true (кнопка «Вся схема») показывает схему целиком, даже если текст станет мелким.
    const scale = clamp(whole === true ? fitScale : Math.max(fitScale, readableScale));
    fitRef.current = scale;
    const place = (viewportSize, contentSize) =>
      contentSize <= viewportSize - FIT_PADDING * 2 ? (viewportSize - contentSize) / 2 : FIT_PADDING;
    changeView({
      scale,
      x: place(viewport.clientWidth, diagram.width * scale),
      y: place(viewport.clientHeight, diagram.height * scale),
    }, true);
  }, [changeView]);

  const zoomAt = useCallback((scale, clientX, clientY) => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const rect = viewport.getBoundingClientRect();
    const pointX = clientX - rect.left;
    const pointY = clientY - rect.top;
    const current = viewRef.current;
    const nextScale = clamp(scale);
    changeView({
      scale: nextScale,
      x: pointX - ((pointX - current.x) / current.scale) * nextScale,
      y: pointY - ((pointY - current.y) / current.scale) * nextScale,
    });
  }, [changeView]);

  const zoomCenter = useCallback((factor) => {
    const rect = viewportRef.current?.getBoundingClientRect();
    if (rect) zoomAt(viewRef.current.scale * factor, rect.left + rect.width / 2, rect.top + rect.height / 2);
  }, [zoomAt]);

  const toggleZoom = useCallback((clientX, clientY) => {
    if (Math.abs(viewRef.current.scale - fitRef.current) < 0.03) {
      zoomAt(Math.max(2, fitRef.current * 2), clientX, clientY);
    } else {
      fit();
    }
  }, [fit, zoomAt]);

  const onRendered = useCallback((svg) => {
    if (!svg) return;
    const box = svg.viewBox?.baseVal;
    const width = box?.width || svg.getBBox().width || 800;
    const height = box?.height || svg.getBBox().height || 600;
    const labels = Array.from(svg.querySelectorAll("text, foreignObject"));
    const fontSizes = labels.map((label) => parseFloat(getComputedStyle(label).fontSize)).filter((value) => value > 0);
    const fontSize = fontSizes.length ? Math.min(...fontSizes) : 14;
    sizeRef.current = { width, height, fontSize };
    setSize(sizeRef.current);
    requestAnimationFrame(fit);
  }, [fit]);

  useEffect(() => {
    const page = document.querySelector(".page");
    if (!page) return undefined;
    const observer = new MutationObserver(() => setIsDark(page.getAttribute("data-theme") === "dark"));
    observer.observe(page, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const opener = document.activeElement;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const handleKey = (event) => {
      if (event.key === "Tab") {
        const controls = Array.from(dialogRef.current?.querySelectorAll("button:not([disabled]), [href], [tabindex]:not([tabindex='-1'])") || []);
        if (!controls.length) return;
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
        return;
      }
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (event.key === "+" || event.key === "=") zoomCenter(1.25);
      else if (event.key === "-" || event.key === "_") zoomCenter(0.8);
      else if (event.key === "0") fit();
      else if (event.key.startsWith("Arrow")) {
        event.preventDefault();
        const current = viewRef.current;
        const step = 48;
        changeView({ ...current,
          x: current.x + (event.key === "ArrowRight" ? -step : event.key === "ArrowLeft" ? step : 0),
          y: current.y + (event.key === "ArrowDown" ? -step : event.key === "ArrowUp" ? step : 0),
        });
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("keydown", handleKey);
      document.body.style.overflow = previousOverflow;
      window.scrollTo(scrollX, scrollY);
      opener?.focus?.({ preventScroll: true });
    };
  }, [changeView, fit, zoomCenter]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;
    const handleWheel = (event) => {
      event.preventDefault();
      const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
      zoomAt(viewRef.current.scale * Math.exp(-delta * (event.ctrlKey ? 0.01 : 0.002)), event.clientX, event.clientY);
    };
    viewport.addEventListener("wheel", handleWheel, { passive: false });
    const observer = new ResizeObserver(() => {
      if (!userAdjusted.current) fit();
    });
    observer.observe(viewport);
    return () => {
      viewport.removeEventListener("wheel", handleWheel);
      observer.disconnect();
    };
  }, [fit, zoomAt]);

  const pointerDown = (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.current.size === 1) {
      gesture.current = { x: event.clientX, y: event.clientY, view: viewRef.current };
      setDragging(true);
    } else if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      const rect = viewportRef.current.getBoundingClientRect();
      const centerX = (a.x + b.x) / 2 - rect.left;
      const centerY = (a.y + b.y) / 2 - rect.top;
      gesture.current = {
        distance: Math.hypot(a.x - b.x, a.y - b.y),
        scale: viewRef.current.scale,
        contentX: (centerX - viewRef.current.x) / viewRef.current.scale,
        contentY: (centerY - viewRef.current.y) / viewRef.current.scale,
      };
    }
  };

  const pointerMove = (event) => {
    if (!pointers.current.has(event.pointerId)) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.current.size === 1 && gesture.current?.view) {
      const start = gesture.current;
      changeView({ ...start.view, x: start.view.x + event.clientX - start.x, y: start.view.y + event.clientY - start.y });
    } else if (pointers.current.size >= 2 && gesture.current?.distance) {
      const [a, b] = [...pointers.current.values()];
      const rect = viewportRef.current.getBoundingClientRect();
      const scale = clamp(gesture.current.scale * Math.hypot(a.x - b.x, a.y - b.y) / Math.max(1, gesture.current.distance));
      changeView({ scale,
        x: (a.x + b.x) / 2 - rect.left - gesture.current.contentX * scale,
        y: (a.y + b.y) / 2 - rect.top - gesture.current.contentY * scale,
      });
    }
  };

  const pointerUp = (event) => {
    // Двойной клик и двойной тап определяем здесь сами: из-за pointer capture браузер
    // не всегда присылает dblclick, а на тач-экранах он может прийти вторым срабатыванием.
    const wasSinglePointer = pointers.current.size === 1 && pointers.current.has(event.pointerId);
    const tapSlop = event.pointerType === "mouse" ? 5 : 12;
    const start = gesture.current;
    pointers.current.delete(event.pointerId);
    if (wasSinglePointer && event.type === "pointerup" && start?.view && Math.hypot(event.clientX - start.x, event.clientY - start.y) < tapSlop) {
      const now = Date.now();
      if (lastTap.current && now - lastTap.current.time < 320 && Math.hypot(event.clientX - lastTap.current.x, event.clientY - lastTap.current.y) < 28) {
        toggleZoom(event.clientX, event.clientY);
        lastTap.current = null;
      } else lastTap.current = { time: now, x: event.clientX, y: event.clientY };
    }
    if (pointers.current.size === 1) {
      const remaining = [...pointers.current.values()][0];
      gesture.current = { ...remaining, view: viewRef.current };
    } else if (!pointers.current.size) {
      gesture.current = null;
      setDragging(false);
    }
  };

  return createPortal(
    <div className={`content-preview-backdrop ${isDark ? "is-dark" : ""}`} onPointerDown={(event) => {
      backdropPressed.current = event.target === event.currentTarget;
    }} onClick={(event) => {
      // Закрываем по click, а не по pointerdown: иначе браузер после закрытия
      // сбрасывает фокус, и он не возвращается на кнопку, открывшую схему.
      if (backdropPressed.current && event.target === event.currentTarget) onCloseRef.current();
      backdropPressed.current = false;
    }}>
      <section ref={dialogRef} className="content-preview-modal is-diagram" role="dialog" aria-modal="true" aria-label="Просмотр схемы Mermaid">
        <div className="diagram-preview-toolbar">
          <div className="content-preview-zoom-controls" aria-label="Масштаб схемы">
            <button type="button" className="content-preview-zoom" onClick={() => zoomCenter(0.8)} aria-label="Уменьшить">−</button>
            <output className="diagram-preview-scale">{Math.round(view.scale * 100)}%</output>
            <button type="button" className="content-preview-zoom" onClick={() => zoomCenter(1.25)} aria-label="Увеличить">+</button>
            <button type="button" className="content-preview-zoom diagram-preview-fit" onClick={() => fit(true)} title="Показать всю схему целиком">Вся схема</button>
          </div>
          <button ref={closeRef} type="button" className="content-preview-close" onClick={() => onCloseRef.current()} aria-label="Закрыть просмотр" title="Закрыть (Esc)"><span aria-hidden="true">✕</span> Закрыть</button>
        </div>
        <div ref={viewportRef} className={`content-preview-body is-diagram ${dragging ? "is-dragging" : ""}`}
          onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp}
          onPointerCancel={pointerUp}>
          <div className="content-preview-diagram-scale" style={{
            width: size?.width || 800, height: size?.height || 600,
            visibility: size ? "visible" : "hidden",
            transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
          }}>
            <MermaidDiagram chart={chart} lessonId={lessonId} blockId={blockId} onRendered={onRendered} />
          </div>
        </div>
      </section>
    </div>, document.body,
  );
}
