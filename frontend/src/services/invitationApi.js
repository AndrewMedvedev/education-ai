/**
 * API-слой карты приглашений курса.
 *
 * Тонкая обёртка над `utils/api.js`: нормализует ответы backend и превращает
 * неуспешные ответы в Error с человекочитаемым `userMessage`.
 *
 * Backend умеет только создавать приглашение (`POST /courses/invitations`),
 * роутов списка, повторной отправки и отмены нет. Поэтому:
 *   - созданное приглашение складывается в локальный список сессии
 *     (`sessionInvitations`), он же отдаётся как страница списка;
 *   - `resendInvitation` / `cancelInvitation` сообщают, что действие пока
 *     не поддерживается сервером.
 *
 * Локальный список живёт до перезагрузки страницы: после неё он пустой,
 * пока на backend не появится GET приглашений курса.
 */
import { createCourseInvitation } from "../utils/api";

/**
 * Флаг демо-режима оставлен только для совместимости: мок-веток в этом модуле
 * больше нет, значение ни на что не влияет. Мок включается исключительно
 * явным VITE_USE_INVITATION_MOCK=true, по умолчанию режим реального API.
 */
export const IS_INVITATION_MOCK =
  String(import.meta.env.VITE_USE_INVITATION_MOCK || "").toLowerCase() ===
  "true";

export const INVITATION_ROLES = ["student", "teacher", "moderator"];

export const INVITATION_ROLE_LABELS = {
  student: "Студент",
  teacher: "Преподаватель",
  moderator: "Модератор",
};

export const INVITATION_STATUSES = ["pending", "accepted", "expired"];

export const INVITATION_STATUS_LABELS = {
  pending: "Ожидает",
  accepted: "Принято",
  // Backend такой статус не отдаёт, строка оставлена как fallback-подпись.
  rejected: "Отклонено",
  expired: "Просрочено",
};

const UNSUPPORTED_MESSAGE = "Действие пока не поддерживается сервером.";

function unsupportedError() {
  const error = new Error(UNSUPPORTED_MESSAGE);
  error.status = 501;
  error.code = "NOT_SUPPORTED";
  error.userMessage = UNSUPPORTED_MESSAGE;
  return error;
}

/** Локальный список приглашений по курсу: живёт до перезагрузки страницы. */
const sessionInvitations = new Map();

function sessionKey(courseId) {
  return String(courseId ?? "");
}

function readSessionInvitations(courseId) {
  return sessionInvitations.get(sessionKey(courseId)) || [];
}

function rememberInvitation(courseId, invitation) {
  sessionInvitations.set(sessionKey(courseId), [
    invitation,
    ...readSessionInvitations(courseId),
  ]);
  return invitation;
}

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

/**
 * Приводит приглашение backend к виду UI. Статус backend не хранит, поэтому
 * считаем его на клиенте: `is_used` → accepted, иначе прошлый `expires_at`
 * → expired, иначе pending.
 */
export function normalizeInvitation(raw = {}) {
  const isUsed = raw.is_used === true || Boolean(raw.used_at);
  const expiresAt = raw.expires_at || raw.expiresAt || "";
  const isExpired =
    !isUsed && Boolean(expiresAt) && Date.parse(expiresAt) < Date.now();
  const status = isUsed ? "accepted" : isExpired ? "expired" : "pending";

  return {
    id: raw.id || raw.invitation_id || raw.invitationId || "",
    email: raw.email || "",
    role: raw.role || "student",
    status,
    createdAt: raw.created_at || raw.createdAt || raw.sent_at || "",
    invitedBy: raw.invited_by || raw.invitedBy || "",
    expiresAt,
  };
}

function paginateSessionInvitations(
  courseId,
  { page = 1, size = 20, status = "" },
) {
  const all = readSessionInvitations(courseId);
  const filtered = status
    ? all.filter((invitation) => invitation.status === status)
    : all;
  const safeSize = Math.max(1, Number(size) || 20);
  const safePage = Math.max(1, Number(page) || 1);
  const start = (safePage - 1) * safeSize;
  const items = filtered
    .slice(start, start + safeSize)
    .map((invitation) => ({ ...invitation }));
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

/**
 * Список приглашений курса. Backend его не отдаёт, поэтому источник данных —
 * приглашения, созданные в текущей сессии страницы.
 */
export async function getCourseInvitations(
  courseId,
  { page = 1, size = 20, status = "" } = {},
) {
  return paginateSessionInvitations(courseId, { page, size, status });
}

/** Создаёт приглашение на backend и запоминает его в сессионном списке. */
export async function inviteToCourse(courseId, { email, role }, options = {}) {
  const response = await createCourseInvitation(
    courseId,
    { email, role },
    options,
  );

  if (!response.ok) {
    throw await parseError(response, "Не удалось отправить приглашение.");
  }

  const data = await response.json().catch(() => null);
  if (!data) return null;

  return rememberInvitation(courseId, normalizeInvitation(data));
}

/** Роута повторной отправки на backend нет. */
export async function resendInvitation() {
  throw unsupportedError();
}

/** Роута отмены приглашения на backend нет. */
export async function cancelInvitation() {
  throw unsupportedError();
}
