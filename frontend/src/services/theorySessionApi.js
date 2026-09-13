import { apiFetch, readStoredSession } from "../utils/api";

const API_BASE = "/api/v1";

async function parseError(response, fallbackMessage) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");
  const detail = payload?.detail || payload?.error?.message || payload;
  const message =
    typeof detail === "string" && detail.trim() ? detail : fallbackMessage;
  const error = new Error(message);
  error.status = response.status;
  error.payload = payload;
  error.userMessage = message;
  return error;
}

export async function createSession(lessonId, options = {}) {
  const response = await apiFetch(
    `/theory/session/${encodeURIComponent(lessonId)}`,
    {
      ...options,
      method: "POST",
    },
    { clearOnUnauthorized: false },
  );

  if (!response.ok) {
    throw await parseError(response, "Не удалось создать сессию теории.");
  }

  return response.json();
}

export async function updateSession(sessionId, metrics, options = {}) {
  const response = await apiFetch(
    `/theory/session/${encodeURIComponent(sessionId)}`,
    {
      ...options,
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      body: JSON.stringify(metrics),
    },
    { clearOnUnauthorized: false },
  );

  if (!response.ok) {
    throw await parseError(response, "Не удалось сохранить метрики теории.");
  }

  return response.json();
}

function normalizeTheorySession(raw = {}) {
  return {
    id: raw.id || "",
    lessonId: raw.lesson_id || raw.lessonId || "",
    userId: raw.user_id || raw.userId || "",
    completedAt: raw.completed_at ?? raw.completedAt ?? null,
    activeTimeSeconds:
      Number(raw.active_time_seconds ?? raw.activeTimeSeconds ?? 0) || 0,
    maxScrollDepthPercent:
      Number(raw.max_scroll_depth_percent ?? raw.maxScrollDepthPercent ?? 0) ||
      0,
    createdAt: raw.created_at || raw.createdAt || "",
    updatedAt: raw.updated_at || raw.updatedAt || "",
  };
}

function buildSessionsQuery(filters = {}) {
  const query = new URLSearchParams();
  if (filters.createdFrom) query.append("created_from", filters.createdFrom);
  if (filters.createdTo) query.append("created_to", filters.createdTo);
  if (filters.sort) query.append("sort", filters.sort);
  return query.toString();
}

export async function getTheorySessions(
  lessonId,
  userId,
  filters = {},
  options = {},
) {
  if (!lessonId || !userId) {
    throw new Error("Для загрузки метрик нужно выбрать урок и студента.");
  }

  const query = buildSessionsQuery(filters);
  const response = await apiFetch(
    `/theory/session/${encodeURIComponent(lessonId)}/${encodeURIComponent(userId)}${query ? `?${query}` : ""}`,
    {
      ...options,
      method: "GET",
    },
    { clearOnUnauthorized: false },
  );

  if (!response.ok) {
    throw await parseError(response, "Не удалось загрузить метрики теории.");
  }

  const data = await response.json();
  return Array.isArray(data) ? data.map(normalizeTheorySession) : [];
}

export function updateSessionKeepalive(sessionId, metrics) {
  const accessToken = readStoredSession().accessToken;

  if (!accessToken || !sessionId) {
    return false;
  }

  fetch(`${API_BASE}/theory/session/${encodeURIComponent(sessionId)}`, {
    method: "PUT",
    keepalive: true,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(metrics),
  }).catch(() => {});

  return true;
}
