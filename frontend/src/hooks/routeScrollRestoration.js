// Retry while asynchronous route content is still shorter than the saved offset.
export function restoreRouteScroll(target, win, done) {
  let frame = null;
  const startedAt = Date.now();
  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    if (frame !== null) win.cancelAnimationFrame(frame);
    for (const event of ["wheel", "touchstart", "keydown", "pointerdown"])
      win.removeEventListener(event, stop);
    done();
  };
  const tick = () => {
    if (stopped) return;
    const height = win.document?.documentElement?.scrollHeight;
    const ready =
      !Number.isFinite(height) || height - win.innerHeight >= target;
    const timedOut = Date.now() - startedAt >= 15000;
    if (ready || timedOut) {
      win.scrollTo({ top: target, left: 0, behavior: "instant" });
      if (Math.abs(win.scrollY - target) <= 1 || timedOut) {
        stop();
        return;
      }
    }
    frame = win.requestAnimationFrame(tick);
  };
  for (const event of ["wheel", "touchstart", "keydown", "pointerdown"])
    win.addEventListener(event, stop, { passive: true });
  frame = win.requestAnimationFrame(tick);
  return stop;
}
