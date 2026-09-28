/**
 * API-слой карты приглашений курса.
 *
 * Тонкая обёртка над `utils/api.js`: нормализует ответы backend и превращает
 * неуспешные ответы в Error с человекочитаемым `userMessage`.
 *
 * TODO: backend endpoint не реализован — роуты согласованы в utils/api.js,
 * функции ниже уже готовы к подключению без правок компонентов.
 */
import {
  cancelCourseInvitation,
  createCourseInvitation,
  listCourseInvitations,
  resendCourseInvitation,
} from "../utils/api";

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
  const response = await listCourseInvitations(
    courseId,
    { page, size, status },
    options,
  );

  if (!response.ok) {
    throw await parseError(response, "Не удалось загрузить приглашения курса.");
  }

  return normalizeInvitationPage(await response.json(), { page, size });
}

export async function inviteToCourse(courseId, { email, role }, options = {}) {
  const response = await createCourseInvitation(courseId, { email, role }, options);

  if (!response.ok) {
    throw await parseError(response, "Не удалось отправить приглашение.");
  }

  const data = await response.json().catch(() => null);
  return data ? normalizeInvitation(data) : null;
}

export async function resendInvitation(courseId, invitationId, options = {}) {
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
  const response = await cancelCourseInvitation(courseId, invitationId, options);

  if (!response.ok) {
    throw await parseError(response, "Не удалось отменить приглашение.");
  }
}
