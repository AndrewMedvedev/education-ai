import { useLayoutEffect, useMemo, useRef } from "react";
import { useAgentStore } from "../stores/agentStore";
import { useSessionStore } from "../stores/sessionStore";
import { getReloadScope } from "../utils/reloadScope";

// Uses the existing scoped agent persistence; no network or File persistence.
export function useAgentInputDraft(key) {
  const scope = useSessionStore(() => getReloadScope());
  const session = useSessionStore((state) => state.sessionContext);
  const token = useMemo(
    () => ({ key, scope, session, alive: true }),
    [key, scope, session],
  );
  const latest = useRef(token);
  latest.current = token;
  useLayoutEffect(() => {
    token.alive = true;
    return () => {
      token.alive = false;
    };
  }, [token]);
  const isCurrent = () =>
    token.alive && latest.current === token && Boolean(scope) &&
    scope === getReloadScope() && session === useSessionStore.getState().sessionContext;
  const input = useAgentStore((state) => state.interviewDrafts?.[key] || "");
  const setInput = (value) => {
    if (isCurrent()) useAgentStore.getState().setInterviewDraft(key, value);
  };
  return [input, setInput, isCurrent];
}
