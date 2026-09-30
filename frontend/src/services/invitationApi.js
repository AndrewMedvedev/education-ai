/**
 * API-слой карты приглашений курса.
 *
 * Тонкая обёртка над `utils/api.js`: нормализует ответы backend и превращает
 * неуспешные ответы в Error с человекочитаемым `userMessage`.
 *
 * Пока backend-эндпоинты карты приглашений не реализованы, слой умеет
 * работать в демо-режиме (in-memory мок): список приглашений виден,
 * «повторить» и «отменить» работают, создание нового приглашения запрещено.
 *
 * Отключить мок и вернуться к реальному API: VITE_USE_INVITATION_MOCK=false
 * (по умолчанию мок включён, чтобы интерфейс был живым без backend).
 */
import {
  cancelCourseInvitation,
  createCourseInvitation,
  listCourseInvitations,
  resendCourseInvitation,
} from "../utils/api";
import { IS_API_MOCK } from "./apiMock";

/**
 * Демо-режим карты приглашений. Явный флаг VITE_USE_INVITATION_MOCK имеет
 * приоритет, иначе повторяем решение общего мок-слоя (`services/apiMock.js`) —
 * так одного VITE_USE_API_MOCK=false достаточно, чтобы вернуть реальный API.
 */
const invitationMockFlag = import.meta.env.VITE_USE_INVITATION_MOCK;

export const IS_INVITATION_MOCK =
  invitationMockFlag === undefined || invitationMockFlag === ""
    ? IS_API_MOCK
    : String(invitationMockFlag).toLowerCase() === "true";

const MOCK_INVITED_BY = "admin";
const MOCK_DAY_MS = 24 * 60 * 60 * 1000;

function mockDelay(ms = 160) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function buildMockSeed() {
  const now = Date.now();

  return [
    {
      id: "mock-1",
      email: "student@example.com",
      role: "student",
      status: "pending",
      createdAt: new Date(now - MOCK_DAY_MS).toISOString(),
      invitedBy: MOCK_INVITED_BY,
    },
    {
      id: "mock-2",
      email: "teacher@example.com",
      role: "teacher",
      status: "accepted",
      createdAt: new Date(now - 3 * MOCK_DAY_MS).toISOString(),
      invitedBy: MOCK_INVITED_BY,
    },
    {
      id: "mock-3",
      email: "moderator@example.com",
      role: "moderator",
      status: "rejected",
      createdAt: new Date(now - 5 * MOCK_DAY_MS).toISOString(),
      invitedBy: MOCK_INVITED_BY,
    },
    {
      id: "mock-4",
      email: "expired@example.com",
      role: "student",
      status: "expired",
      createdAt: new Date(now - 10 * MOCK_DAY_MS).toISOString(),
      invitedBy: MOCK_INVITED_BY,
    },
  ];
}

/** In-memory хранилище моков: живёт до перезагрузки страницы. */
const mockInvitationsByCourse = new Map();

function mockKey(courseId) {
  return String(courseId ?? "demo-course");
}

/**
 * Возвращает список приглашений курса из мока. Для первого обращения
 * курс инициализируется предустановленным набором из четырёх записей.
 */
export function getMockInvitations(courseId) {
  const key = mockKey(courseId);

  if (!mockInvitationsByCourse.has(key)) {
    mockInvitationsByCourse.set(key, buildMockSeed());
  }

  return mockInvitationsByCourse.get(key);
}

function cloneInvitation(invitation) {
  return { ...invitation };
}

function createMockReadOnlyError() {
  const error = new Error(
    "Создание приглашений недоступно в демо-режиме (нет бэкенда).",
  );
  error.code = "MOCK_READ_ONLY";
  error.userMessage = error.message;
  return error;
}

async function getMockInvitationPage(
  courseId,
  { page = 1, size = 20, status = "" } = {},
) {
  await mockDelay();

  const all = getMockInvitations(courseId);
  const filtered = status
    ? all.filter((invitation) => invitation.status === status)
    : all;
  const safeSize = Math.max(1, Number(size) || 20);
  const safePage = Math.max(1, Number(page) || 1);
  const start = (safePage - 1) * safeSize;
  const items = filtered.slice(start, start + safeSize).map(cloneInvitation);
  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / safeSize));

  return {
    items,
    page: safePage,
    size: safeSize,
    total,
    pages,
    total_pages: pages,
    has_next: safePage < pages,
    has_prev: safePage > 1,
  };
}

export const INVITATION_ROLES = ["student", "teacher", "moderator"];

export const INVITATION_ROLE_LABELS = {
  student: "Студент",
  teacher: "Преподаватель",
  moderator: "Модератор",
};

export const INVITATION_STATUSES = [
  "pending",
  "accepted",
  "rejected",
  "expired",
];

export const INVITATION_STATUS_LABELS = {
  pending: "Ожидает",
  accepted: "Принято",
  rejected: "Отклонено",
  expired: "Просрочено",
};

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

export function normalizeInvitation(raw = {}) {
  const status = String(raw.status || "pending").toLowerCase();

  return {
    id: raw.id || raw.invitation_id || raw.invitationId || "",
    email: raw.email || "",
    role: raw.role || "student",
    status: INVITATION_STATUSES.includes(status) ? status : "pending",
    createdAt: raw.created_at || raw.createdAt || raw.sent_at || "",
    invitedBy: raw.invited_by || raw.invitedBy || "",
  };
}

function normalizeInvitationPage(data, { page = 1, size = 20 } = {}) {
  const rawItems = Array.isArray(data)
    ? data
    : data?.items || data?.invitations || data?.results || [];
  const items = rawItems.map(normalizeInvitation);
  const total = Number(data?.total) || items.length;
  const pages =
    Number(data?.pages) ||
    Number(data?.total_pages) ||
    Math.max(1, Math.ceil(total / Math.max(1, size)));

  return {
    items,
    page: Number(data?.page) || page,
    size: Number(data?.size) || size,
    total,
    pages,
    total_pages: pages,
    has_next: Boolean(data?.has_next ?? data?.hasNext ?? page < pages),
    has_prev: Boolean(data?.has_prev ?? data?.hasPrev ?? page > 1),
  };
}

export async function getCourseInvitations(
  courseId,
  { page = 1, size = 20, status = "" } = {},
  options = {},
) {
  if (IS_INVITATION_MOCK) {
    return getMockInvitationPage(courseId, { page, size, status });
  }

  const response = await listCourseInvitations(
    courseId,
    { page, size, status },
    options,
  );

  if (!response.ok) {
    if (response.status === 404) {
      const error = new Error(
        "Список приглашений курса пока не подключён на сервере (endpoint не найден).",
      );
      error.status = response.status;
      error.userMessage = error.message;
      throw error;
    }

    throw await parseError(response, "Не удалось загрузить приглашения курса.");
  }

  return normalizeInvitationPage(await response.json(), { page, size });
}

export async function inviteToCourse(courseId, { email, role }, options = {}) {
  if (IS_INVITATION_MOCK) {
    // Демо-режим: приглашения создаются только на backend, которого нет.
    throw createMockReadOnlyError();
  }

  const response = await createCourseInvitation(courseId, { email, role }, options);

  if (!response.ok) {
    throw await parseError(response, "Не удалось отправить приглашение.");
  }

  const data = await response.json().catch(() => null);
  return data ? normalizeInvitation(data) : null;
}

export async function resendInvitation(courseId, invitationId, options = {}) {
  if (IS_INVITATION_MOCK) {
    await mockDelay();

    const list = getMockInvitations(courseId);
    const index = list.findIndex((item) => item.id === invitationId);
    const current = list[index];

    if (index === -1) {
      const error = new Error("Приглашение не найдено в демо-данных.");
      error.userMessage = error.message;
      throw error;
    }

    const updated = {
      ...current,
      status: "pending",
      createdAt: new Date().toISOString(),
    };
    list[index] = updated;

    return cloneInvitation(updated);
  }

  const response = await resendCourseInvitation(courseId, invitationId, options);

  if (!response.ok) {
    throw await parseError(
      response,
      "Не удалось отправить приглашение повторно.",
    );
  }

  const data = await response.json().catch(() => null);
  return data ? normalizeInvitation(data) : null;
}

export async function cancelInvitation(courseId, invitationId, options = {}) {
  if (IS_INVITATION_MOCK) {
    await mockDelay();

    const list = getMockInvitations(courseId);
    const index = list.findIndex((item) => item.id === invitationId);

    if (index === -1) {
      const error = new Error("Приглашение не найдено в демо-данных.");
      error.userMessage = error.message;
      throw error;
    }

    list.splice(index, 1);
    return;
  }

  const response = await cancelCourseInvitation(courseId, invitationId, options);

  if (!response.ok) {
    throw await parseError(response, "Не удалось отменить приглашение.");
  }
}
