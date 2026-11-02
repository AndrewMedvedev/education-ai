export function pollPracticeGeneration({ load, apply, isCurrent, isSending, onError, schedule = setTimeout, cancel = clearTimeout }) {
  let stopped = false;
  let timer;
  const poll = async () => {
    if (stopped || !isCurrent()) return;
    if (isSending()) {
      timer = schedule(poll, 1000);
      return;
    }
    try {
      const job = await load();
      if (stopped || !isCurrent()) return;
      await apply(job);
      if (!stopped && isCurrent() && ["queued", "running"].includes(job?.status)) timer = schedule(poll, 3000);
    } catch (error) {
      if (!stopped && isCurrent()) {
        const terminal = [401, 403, 404].includes(error?.status);
        onError(error, terminal);
        if (!terminal) timer = schedule(poll, 5000);
      }
    }
  };
  timer = schedule(poll, 3000);
  return () => { stopped = true; cancel(timer); };
}
