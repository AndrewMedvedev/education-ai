import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useUiLayoutStore } from "../stores/uiLayoutStore";

const getRouteScrollKey = (location) =>
  `${location.pathname}${location.search || ""}`;

export function useRouteScrollRestoration() {
  const location = useLocation();
  const saveScrollPosition = useUiLayoutStore(
    (state) => state.saveScrollPosition,
  );
  const getScrollPosition = useUiLayoutStore(
    (state) => state.getScrollPosition,
  );
  const hasHydrated = useUiLayoutStore((state) => state.hasHydrated);
  const currentRouteKeyRef = useRef(getRouteScrollKey(location));
  const lastScrollYRef = useRef(
    typeof window === "undefined" ? 0 : window.scrollY,
  );
  const frameRef = useRef(null);
  const hasRestoredInitialRouteRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    const previousRestoration = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";

    return () => {
      window.history.scrollRestoration = previousRestoration;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    const handleScroll = () => {
      lastScrollYRef.current = window.scrollY;

      if (frameRef.current !== null) return;
      frameRef.current = window.requestAnimationFrame(() => {
        frameRef.current = null;
        saveScrollPosition(currentRouteKeyRef.current, lastScrollYRef.current);
      });
    };

    const handleBeforeUnload = () => {
      saveScrollPosition(currentRouteKeyRef.current, window.scrollY);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
      }
      saveScrollPosition(currentRouteKeyRef.current, window.scrollY);
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [saveScrollPosition]);

  useEffect(() => {
    if (!hasHydrated || typeof window === "undefined") return undefined;

    const previousRouteKey = currentRouteKeyRef.current;
    const nextRouteKey = getRouteScrollKey(location);

    if (
      hasRestoredInitialRouteRef.current &&
      previousRouteKey !== nextRouteKey
    ) {
      saveScrollPosition(previousRouteKey, window.scrollY);
    }

    currentRouteKeyRef.current = nextRouteKey;
    hasRestoredInitialRouteRef.current = true;

    const restoreFrame = window.requestAnimationFrame(() => {
      const savedScrollY = getScrollPosition(nextRouteKey);
      window.scrollTo({
        top: typeof savedScrollY === "number" ? savedScrollY : 0,
        left: 0,
        behavior: "auto",
      });
    });

    return () => window.cancelAnimationFrame(restoreFrame);
  }, [getScrollPosition, hasHydrated, location, saveScrollPosition]);
}
