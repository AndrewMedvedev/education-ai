// Крупные всплывающие подсказки для конструктора курса вместо системных title:
// системную подсказку не увеличить, а пользователям нужен текст, который легко прочитать.
// Подсказка берётся из атрибута data-tip, рисуется поверх холста и не зависит от масштаба.
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const SHOW_DELAY_MS = 350;
const EDGE_GAP = 12;
const MAX_WIDTH = 320;

function findTipTarget(element) {
  const target = element?.closest?.("[data-tip]");
  if (!target || !target.closest(".dnd-builder")) return null;
  return target.getAttribute("data-tip") ? target : null;
}

export default function DndTooltipLayer() {
  const [tip, setTip] = useState(null);
  const targetRef = useRef(null);
  const timerRef = useRef(0);
  const frameRef = useRef(0);

  useEffect(() => {
    const hide = () => {
      window.clearTimeout(timerRef.current);
      targetRef.current = null;
      setTip(null);
    };

    const show = (element) => {
      const text = element.getAttribute("data-tip");
      if (!text || !element.isConnected) {
        setTip(null);
        return;
      }
      const rect = element.getBoundingClientRect();
      const half = Math.min(MAX_WIDTH, window.innerWidth - EDGE_GAP * 2) / 2;
      const center = rect.left + rect.width / 2;
      setTip({
        text,
        x: Math.min(
          Math.max(center, EDGE_GAP + half),
          window.innerWidth - EDGE_GAP - half,
        ),
        y: rect.top > 72 ? rect.top : rect.bottom,
        place: rect.top > 72 ? "top" : "bottom",
      });
    };

    const updateTarget = (element) => {
      if (element === targetRef.current) return;
      window.clearTimeout(timerRef.current);
      targetRef.current = element;
      setTip(null);
      if (!element) return;
      timerRef.current = window.setTimeout(() => {
        if (targetRef.current === element) show(element);
      }, SHOW_DELAY_MS);
    };

    // elementFromPoint находит и отключённые кнопки: на них браузер не шлёт события
    // мыши, а подсказка вроде «удалить нельзя» там нужна больше всего.
    const onPointerMove = (event) => {
      if (event.pointerType === "touch") return;
      const { clientX, clientY } = event;
      window.cancelAnimationFrame(frameRef.current);
      frameRef.current = window.requestAnimationFrame(() => {
        updateTarget(
          findTipTarget(document.elementFromPoint(clientX, clientY)),
        );
      });
    };

    const onFocusIn = (event) => {
      const element = findTipTarget(event.target);
      if (!element || !element.matches(":focus-visible")) return;
      window.clearTimeout(timerRef.current);
      targetRef.current = element;
      show(element);
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") hide();
    };

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerdown", hide, true);
    window.addEventListener("wheel", hide, { passive: true });
    window.addEventListener("scroll", hide, true);
    window.addEventListener("blur", hide);
    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("focusout", hide);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(timerRef.current);
      window.cancelAnimationFrame(frameRef.current);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerdown", hide, true);
      window.removeEventListener("wheel", hide);
      window.removeEventListener("scroll", hide, true);
      window.removeEventListener("blur", hide);
      document.removeEventListener("focusin", onFocusIn);
      document.removeEventListener("focusout", hide);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  if (!tip) return null;

  return createPortal(
    <div
      className={`dnd-tooltip is-${tip.place}`}
      role="tooltip"
      style={{ left: tip.x, top: tip.y }}
    >
      {tip.text}
    </div>,
    document.querySelector(".page") || document.body,
  );
}
