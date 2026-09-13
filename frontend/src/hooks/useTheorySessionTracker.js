import { useCallback, useEffect, useRef } from "react";
import {
  createSession,
  updateSession,
  updateSessionKeepalive,
} from "../services/theorySessionApi";
import { useActiveTimeTracker } from "./useActiveTimeTracker";

const SCROLL_THROTTLE_MS = 250;
const createSessionPromises = new Map();
const completedSessionIds = new Set();

function buildMetrics(activeTimeSeconds, maxScrollDepthPercent) {
  return {
    completed_at: new Date().toISOString(),
    active_time_seconds: Math.max(0, Math.round(activeTimeSeconds || 0)),
    max_scroll_depth_percent: Math.min(
      100,
      Math.max(0, Math.round(maxScrollDepthPercent || 0)),
    ),
  };
}

function clampPercent(value) {
  return Math.min(100, Math.max(0, value));
}

function getViewportHeight() {
  return (
    window.visualViewport?.height ||
    window.innerHeight ||
    document.documentElement.clientHeight ||
    0
  );
}

function isElementScrollable(element) {
  if (!element) return false;
  const overflowY = window.getComputedStyle(element).overflowY;
  return (
    element.scrollHeight > element.clientHeight + 1 &&
    ["auto", "scroll", "overlay"].includes(overflowY)
  );
}

function getElementScrollPercent(element) {
  const scrollableDistance = element.scrollHeight - element.clientHeight;

  if (scrollableDistance <= 0) {
    return 100;
  }

  return clampPercent((element.scrollTop / scrollableDistance) * 100);
}

function getWindowScrollPercentForContent(contentElement) {
  if (!contentElement) {
    return 0;
  }

  const rect = contentElement.getBoundingClientRect();
  const pageScrollTop =
    window.scrollY || document.documentElement.scrollTop || 0;
  const contentTop = rect.top + pageScrollTop;
  const contentHeight = contentElement.scrollHeight || rect.height || 0;
  const viewportHeight = getViewportHeight();
  const maxTheoryScroll = contentHeight - viewportHeight;

  if (contentHeight <= 0) {
    return 0;
  }

  if (maxTheoryScroll <= 0) {
    return rect.top <= 0 ? 100 : 0;
  }

  return clampPercent(((pageScrollTop - contentTop) / maxTheoryScroll) * 100);
}

function createLessonSessionOnce(lessonId) {
  const existingPromise = createSessionPromises.get(lessonId);
  if (existingPromise) {
    return existingPromise;
  }

  const promise = createSession(lessonId).finally(() => {
    createSessionPromises.delete(lessonId);
  });
  createSessionPromises.set(lessonId, promise);
  return promise;
}

export function useTheorySessionTracker(
  lessonId,
  {
    enabled = true,
    scrollContainerRef = null,
    contentRef = null,
    isContentReady = true,
  } = {},
) {
  const sessionRef = useRef(null);
  const sessionPromiseRef = useRef(null);
  const activeTimeSecondsRef = useRef(0);
  const maxScrollDepthRef = useRef(0);
  const lastScrollMeasureAtRef = useRef(0);
  const latestLessonIdRef = useRef(lessonId);
  const isContentReadyRef = useRef(isContentReady);

  latestLessonIdRef.current = lessonId;
  isContentReadyRef.current = isContentReady;

  const handleActiveTimeTick = useCallback((seconds) => {
    activeTimeSecondsRef.current = seconds;
  }, []);

  const { markActivity, reset } = useActiveTimeTracker({
    enabled: enabled && Boolean(lessonId),
    resetKey: lessonId || "",
    targets: scrollContainerRef ? [scrollContainerRef] : [],
    onTick: handleActiveTimeTick,
  });

  const updateScrollDepth = useCallback(
    (force = false) => {
      if (!isContentReadyRef.current) {
        return;
      }

      const now = Date.now();
      if (!force && now - lastScrollMeasureAtRef.current < SCROLL_THROTTLE_MS) {
        return;
      }
      lastScrollMeasureAtRef.current = now;

      const contentElement = contentRef?.current;
      if (!contentElement) {
        return;
      }

      const scrollContainer = scrollContainerRef?.current;
      const depth = isElementScrollable(scrollContainer)
        ? getElementScrollPercent(scrollContainer)
        : getWindowScrollPercentForContent(contentElement);

      if (depth > maxScrollDepthRef.current) {
        maxScrollDepthRef.current = depth;
      }
      markActivity();
    },
    [contentRef, markActivity, scrollContainerRef],
  );

  const getMetricsSnapshot = useCallback(() => {
    updateScrollDepth(true);
    return buildMetrics(
      activeTimeSecondsRef.current,
      maxScrollDepthRef.current,
    );
  }, [updateScrollDepth]);

  const finalizeSession = useCallback(
    (session, metrics, { keepalive = false } = {}) => {
      if (!session?.id || completedSessionIds.has(session.id)) {
        return false;
      }

      completedSessionIds.add(session.id);

      if (keepalive) {
        return updateSessionKeepalive(session.id, metrics);
      }

      updateSession(session.id, metrics).catch((error) => {
        if (error?.status === 404) {
          return;
        }
      });
      return true;
    },
    [],
  );

  const finishCurrentSession = useCallback(
    ({ keepalive = false } = {}) => {
      const metrics = getMetricsSnapshot();
      const currentSession = sessionRef.current;
      const currentSessionPromise = sessionPromiseRef.current;

      sessionRef.current = null;
      sessionPromiseRef.current = null;

      if (currentSession?.id) {
        return finalizeSession(currentSession, metrics, { keepalive });
      }

      if (currentSessionPromise) {
        currentSessionPromise
          .then((session) => finalizeSession(session, metrics, { keepalive }))
          .catch(() => {});
        return true;
      }

      return false;
    },
    [finalizeSession, getMetricsSnapshot],
  );

  useEffect(() => {
    if (!enabled || !lessonId) {
      return undefined;
    }

    activeTimeSecondsRef.current = 0;
    maxScrollDepthRef.current = 0;
    lastScrollMeasureAtRef.current = 0;
    reset();
    markActivity();

    let isCancelled = false;
    const sessionPromise = createLessonSessionOnce(lessonId);
    sessionPromiseRef.current = sessionPromise;

    sessionPromise
      .then((session) => {
        if (isCancelled || latestLessonIdRef.current !== lessonId) {
          return;
        }
        sessionRef.current = session;
      })
      .catch(() => {
        if (sessionPromiseRef.current === sessionPromise) {
          sessionPromiseRef.current = null;
        }
      });

    return () => {
      isCancelled = true;
      finishCurrentSession();
    };
  }, [enabled, finishCurrentSession, lessonId, markActivity, reset]);

  useEffect(() => {
    const scrollContainer = scrollContainerRef?.current;
    if (!enabled || !lessonId || !isContentReady || !contentRef?.current) {
      return undefined;
    }

    const handleScroll = () => updateScrollDepth(false);
    const handleResize = () => updateScrollDepth(true);

    if (scrollContainer) {
      scrollContainer.addEventListener("scroll", handleScroll, {
        passive: true,
      });
    }
    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleResize);
    updateScrollDepth(true);

    return () => {
      if (scrollContainer) {
        scrollContainer.removeEventListener("scroll", handleScroll);
      }
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleResize);
    };
  }, [
    contentRef,
    enabled,
    isContentReady,
    lessonId,
    scrollContainerRef,
    updateScrollDepth,
  ]);

  useEffect(() => {
    if (!enabled || !lessonId) {
      return undefined;
    }

    const handlePageHide = () => {
      finishCurrentSession({ keepalive: true });
    };

    window.addEventListener("pagehide", handlePageHide);
    return () => window.removeEventListener("pagehide", handlePageHide);
  }, [enabled, finishCurrentSession, lessonId]);
}
