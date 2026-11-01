import { useEffect, useLayoutEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useUiLayoutStore } from "../stores/uiLayoutStore";
import { restoreRouteScroll } from "./routeScrollRestoration.js";
import { useSessionStore } from "../stores/sessionStore";
import { getReloadScope } from "../utils/reloadScope";

export function useRouteScrollRestoration() {
  const location = useLocation();
  const scope = useSessionStore(() => getReloadScope());
  const routeKey = scope
    ? JSON.stringify([scope, location.pathname, location.search || ""])
    : null;
  const save = useUiLayoutStore((state) => state.saveScrollPosition);
  const get = useUiLayoutStore((state) => state.getScrollPosition);
  const hydrated = useUiLayoutStore((state) => state.hasHydrated);
  const current = useRef(routeKey);
  const lastY = useRef(typeof window === "undefined" ? 0 : window.scrollY);
  const frame = useRef(null);
  const restoring = useRef(false);
  const restored = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const previous = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    return () => {
      window.history.scrollRestoration = previous;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const flush = () => {
      if (!restoring.current && restored.current)
        save(current.current, lastY.current);
    };
    const scroll = () => {
      if (restoring.current || !restored.current) return;
      lastY.current = window.scrollY;
      if (frame.current !== null) return;
      const key = current.current;
      frame.current = window.requestAnimationFrame(() => {
        frame.current = null;
        save(key, lastY.current);
      });
    };
    window.addEventListener("scroll", scroll, { passive: true });
    window.addEventListener("pagehide", flush);
    window.addEventListener("beforeunload", flush);
    return () => {
      if (frame.current !== null) window.cancelAnimationFrame(frame.current);
      frame.current = null;
      flush();
      window.removeEventListener("scroll", scroll);
      window.removeEventListener("pagehide", flush);
      window.removeEventListener("beforeunload", flush);
    };
  }, [save]);

  useLayoutEffect(() => {
    if (!hydrated || typeof window === "undefined") return undefined;
    if (!routeKey) {
      restored.current = false;
      current.current = null;
      return undefined;
    }
    if (frame.current !== null) window.cancelAnimationFrame(frame.current);
    frame.current = null;
    if (restored.current && current.current !== routeKey)
      save(current.current, lastY.current);
    // Read before any scroll event can overwrite the destination position.
    const saved = get(routeKey);
    const target = Number.isFinite(saved) ? Math.max(0, saved) : 0;
    current.current = routeKey;
    restored.current = true;
    restoring.current = true;
    return restoreRouteScroll(target, window, () => {
      restoring.current = false;
      lastY.current = window.scrollY;
    });
  }, [get, hydrated, routeKey, save]);
}
