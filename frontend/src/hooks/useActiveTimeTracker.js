import { useCallback, useEffect, useRef } from "react";

export const DEFAULT_IDLE_TIMEOUT_MS = 20_000;
export const DEFAULT_ACTIVITY_THROTTLE_MS = 250;

export function useActiveTimeTracker({
  enabled = true,
  idleTimeoutMs = DEFAULT_IDLE_TIMEOUT_MS,
  activityThrottleMs = DEFAULT_ACTIVITY_THROTTLE_MS,
  resetKey = "",
  targets = [],
  onTick,
} = {}) {
  const activeSecondsRef = useRef(0);
  const intervalRef = useRef(null);
  const idleTimeoutRef = useRef(null);
  const lastActivityAtRef = useRef(0);
  const isActiveRef = useRef(false);

  const stopTicking = useCallback(() => {
    isActiveRef.current = false;
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startTicking = useCallback(() => {
    if (!enabled || document.hidden) {
      stopTicking();
      return;
    }

    isActiveRef.current = true;
    if (!intervalRef.current) {
      intervalRef.current = window.setInterval(() => {
        if (!document.hidden && isActiveRef.current) {
          activeSecondsRef.current += 1;
          onTick?.(activeSecondsRef.current);
        }
      }, 1000);
    }
  }, [enabled, onTick, stopTicking]);

  const markActivity = useCallback(() => {
    if (!enabled || document.hidden) {
      return;
    }

    const now = Date.now();
    if (now - lastActivityAtRef.current < activityThrottleMs) {
      return;
    }

    lastActivityAtRef.current = now;
    startTicking();

    if (idleTimeoutRef.current) {
      clearTimeout(idleTimeoutRef.current);
    }
    idleTimeoutRef.current = window.setTimeout(stopTicking, idleTimeoutMs);
  }, [activityThrottleMs, enabled, idleTimeoutMs, startTicking, stopTicking]);

  const reset = useCallback(() => {
    activeSecondsRef.current = 0;
    lastActivityAtRef.current = 0;
    if (idleTimeoutRef.current) {
      clearTimeout(idleTimeoutRef.current);
      idleTimeoutRef.current = null;
    }
    stopTicking();
  }, [stopTicking]);

  const getActiveTimeSeconds = useCallback(
    () => Math.max(0, Math.round(activeSecondsRef.current)),
    [],
  );

  useEffect(() => {
    reset();
  }, [reset, resetKey]);

  useEffect(() => {
    if (!enabled) {
      reset();
      return undefined;
    }

    const activityOptions = { passive: true, capture: true };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopTicking();
      } else if (Date.now() - lastActivityAtRef.current <= idleTimeoutMs) {
        startTicking();
      }
    };

    window.addEventListener("mousemove", markActivity, activityOptions);
    window.addEventListener("scroll", markActivity, activityOptions);
    window.addEventListener("keydown", markActivity, true);
    window.addEventListener("input", markActivity, true);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    const resolvedTargets = targets
      .map((target) => {
        if (!target) return null;
        if (typeof target.addEventListener === "function") return target;
        return target.current || null;
      })
      .filter((target) => typeof target?.addEventListener === "function");
    resolvedTargets.forEach((target) => {
      target.addEventListener("scroll", markActivity, activityOptions);
      target.addEventListener("input", markActivity, true);
      target.addEventListener("keydown", markActivity, true);
    });

    return () => {
      window.removeEventListener("mousemove", markActivity, activityOptions);
      window.removeEventListener("scroll", markActivity, activityOptions);
      window.removeEventListener("keydown", markActivity, true);
      window.removeEventListener("input", markActivity, true);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      resolvedTargets.forEach((target) => {
        target.removeEventListener("scroll", markActivity, activityOptions);
        target.removeEventListener("input", markActivity, true);
        target.removeEventListener("keydown", markActivity, true);
      });
      if (idleTimeoutRef.current) {
        clearTimeout(idleTimeoutRef.current);
      }
      stopTicking();
    };
  }, [
    enabled,
    idleTimeoutMs,
    markActivity,
    reset,
    startTicking,
    stopTicking,
    targets,
  ]);

  return { getActiveTimeSeconds, markActivity, reset };
}
