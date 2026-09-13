import { apiFetch, mapCourseFromApi } from "../utils/api";

function normalizePaginatedCourses(data, { page = 1, size = 10 } = {}) {
  const rawItems = Array.isArray(data)
    ? data
    : data?.items || data?.courses || data?.results || [];
  const items = rawItems.map(mapCourseFromApi);
  const total =
    Number(data?.total) || Number(data?.total_items) || items.length;
  const pages =
    Number(data?.pages) ||
    Number(data?.total_pages) ||
    Math.max(1, Math.ceil(total / Math.max(1, size)));

  return {
    ...data,
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

export async function signCourse(courseId, options = {}) {
  const response = await apiFetch(
    `/student/${encodeURIComponent(courseId)}/sign`,
    {
      ...options,
      method: "POST",
    },
  );

  if (!response.ok) {
    throw await parseError(response, "Не удалось записаться на курс.");
  }

  return response.json();
}

function normalizeStudent(raw = {}) {
  return {
    id: raw.id || "",
    courseId: raw.course_id || raw.courseId || "",
    userId: raw.user_id || raw.userId || "",
    createdAt: raw.created_at || raw.createdAt || "",
    updatedAt: raw.updated_at || raw.updatedAt || "",
    deletedAt: raw.deleted_at ?? raw.deletedAt ?? null,
  };
}

function normalizeStudentPage(data, { page = 1, size = 10 } = {}) {
  const items = (data?.items || []).map(normalizeStudent);
  const total = Number(data?.total) || items.length;
  const pages =
    Number(data?.pages) || Math.max(1, Math.ceil(total / Math.max(1, size)));

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

function normalizeUser(raw = {}) {
  return {
    id: raw.id || raw.user_id || raw.userId || "",
    fullName: raw.fullName || raw.full_name || "",
    avatarUrl: raw.avatarUrl || raw.avatar_url || "",
    email: raw.email || "",
    username: raw.username || "",
    isActive: raw.isActive ?? raw.is_active ?? true,
    createdAt: raw.createdAt || raw.created_at || "",
    updatedAt: raw.updatedAt || raw.updated_at || "",
  };
}

export async function getCourseStudents(
  courseId,
  { page = 1, size = 10 } = {},
  options = {},
) {
  const response = await apiFetch(`/student/${encodeURIComponent(courseId)}`, {
    ...options,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    body: JSON.stringify({ page, size }),
  });

  if (!response.ok) {
    throw await parseError(response, "Не удалось загрузить студентов курса.");
  }

  const data = await response.json();
  return normalizeStudentPage(data, { page, size });
}

export async function getUserById(userId, options = {}) {
  const response = await apiFetch(`/users/${encodeURIComponent(userId)}`, {
    ...options,
    method: "GET",
  });

  if (!response.ok) {
    throw await parseError(
      response,
      "Не удалось загрузить данные пользователя.",
    );
  }

  return normalizeUser(await response.json());
}

export async function getMyCourses({ page = 1, size = 10 } = {}, options = {}) {
  const response = await apiFetch("/student/", {
    ...options,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    body: JSON.stringify({ page, size }),
  });

  if (!response.ok) {
    throw await parseError(response, "Не удалось загрузить ваши курсы.");
  }

  const data = await response.json();
  return normalizePaginatedCourses(data, { page, size });
}
