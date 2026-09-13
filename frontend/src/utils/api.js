import { getMediaId } from "./media";
import { getLocalStorage } from "./storage";

const SESSION_KEY = "aicolab_session";
const API_BASE = "/api/v1";
const REFRESH_SKEW_SECONDS = 30;

let refreshPromise = null;
let unauthorizedHandler = null;
let tokenChangeHandler = null;
const tokenEventTarget =
  typeof EventTarget !== "undefined" ? new EventTarget() : null;

export class ApiError extends Error {
  constructor(message, { status, code, validationErrors, payload } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.validationErrors = validationErrors || {};
    this.payload = payload;
    this.userMessage = message;
  }
}

export function readStoredSession() {
  const storage = getLocalStorage();
  if (!storage) {
    return emptySession();
  }

  try {
    const value = JSON.parse(storage.getItem(SESSION_KEY) || "null");
    return {
      accessToken: value?.accessToken || null,
      refreshToken: value?.refreshToken || null,
      expiresAt: Number(value?.expiresAt) || null,
      membershipId: value?.membershipId || null,
      organizationId: value?.organizationId || null,
    };
  } catch {
    return emptySession();
  }
}

export function saveStoredSession(session) {
  const storage = getLocalStorage();
  if (!storage) return;

  if (!session) {
    storage.removeItem(SESSION_KEY);
    storage.removeItem("user");
    emitTokenChange(emptySession());
    return;
  }

  // Компромисс: backend возвращает bearer-токены в тело ответа, httpOnly cookie
  // здесь недоступны без изменения контракта API. Храним в localStorage для
  // восстановления сессии после перезагрузки; TODO: заменить на httpOnly cookies
  // или in-memory access token + refresh cookie, когда backend поддержит это.
  const nextSession = {
    accessToken: session.accessToken || null,
    refreshToken: session.refreshToken || null,
    expiresAt: Number(session.expiresAt) || null,
    membershipId: session.membershipId || null,
    organizationId: session.organizationId || null,
  };
  storage.setItem(SESSION_KEY, JSON.stringify(nextSession));
  emitTokenChange(nextSession);
}

function emptySession() {
  return {
    accessToken: null,
    refreshToken: null,
    expiresAt: null,
    membershipId: null,
    organizationId: null,
  };
}

function getTokens() {
  const session = readStoredSession();
  return {
    access: session.accessToken,
    refresh: session.refreshToken,
    expiresAt: session.expiresAt,
  };
}

function emitTokenChange(session) {
  if (typeof tokenChangeHandler === "function") {
    tokenChangeHandler(session);
  }
  tokenEventTarget?.dispatchEvent(new Event("tokenRefreshed"));
}

export function onTokenRefreshed(callback) {
  if (!tokenEventTarget || typeof callback !== "function") {
    return () => {};
  }
  tokenEventTarget.addEventListener("tokenRefreshed", callback);
  return () => tokenEventTarget.removeEventListener("tokenRefreshed", callback);
}

export function isTokenExpired(expiresAt = readStoredSession().expiresAt) {
  return !expiresAt || shouldRefresh(Number(expiresAt));
}

export const tokenStorage = {
  getAccessToken: () => readStoredSession().accessToken,
  getRefreshToken: () => readStoredSession().refreshToken,
  setTokens: (accessToken, refreshToken, expiresAt) => {
    const current = readStoredSession();
    saveStoredSession({
      ...current,
      accessToken,
      refreshToken,
      expiresAt,
    });
  },
  clearTokens: () => saveStoredSession(null),
  isTokenExpired,
};

function decodeJwtExp(token) {
  if (!token || typeof token !== "string") return null;

  try {
    const encodedPayload = token.split(".")[1] || "";
    const base64Payload = encodedPayload
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(encodedPayload.length / 4) * 4, "=");
    const payload = JSON.parse(atob(base64Payload));
    return Number(payload?.exp) || null;
  } catch {
    return null;
  }
}

function normalizeExpiresAt(value, accessToken) {
  if (value === null || value === undefined || value === "") {
    return decodeJwtExp(accessToken);
  }

  const numericValue = Number(value);
  if (Number.isFinite(numericValue) && numericValue > 0) {
    return numericValue > 9999999999
      ? Math.floor(numericValue / 1000)
      : numericValue;
  }

  const parsedDate = Date.parse(value);
  if (Number.isFinite(parsedDate)) {
    return Math.floor(parsedDate / 1000);
  }

  return decodeJwtExp(accessToken);
}

function normalizeTokenResponse(data) {
  const source = data?.tokens || data?.data || data || {};
  const accessToken =
    source.access_token || source.accessToken || source.access || null;
  const refreshToken =
    source.refresh_token || source.refreshToken || source.refresh || null;
  const rawExpiresAt =
    source.expires_at ||
    source.expiresAt ||
    source.exp ||
    source.access_expires_at ||
    source.accessTokenExpiresAt;

  return {
    accessToken,
    refreshToken,
    expiresAt: normalizeExpiresAt(rawExpiresAt, accessToken),
  };
}

function saveTokensFromResponse(data) {
  const current = readStoredSession();
  const tokens = normalizeTokenResponse(data);
  const nextSession = {
    ...current,
    accessToken: tokens.accessToken || current.accessToken,
    refreshToken: tokens.refreshToken || current.refreshToken,
    expiresAt: tokens.expiresAt || current.expiresAt,
  };
  saveStoredSession(nextSession);
  return nextSession;
}

function clearTokens() {
  saveStoredSession(null);
}

function shouldRefresh(expiresAt) {
  if (!expiresAt) return false;
  return expiresAt <= Math.floor(Date.now() / 1000) + REFRESH_SKEW_SECONDS;
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

export function setTokenChangeHandler(handler) {
  tokenChangeHandler = handler;
}

export function isAuthenticated() {
  const { access, refresh, expiresAt } = getTokens();
  return Boolean(
    access && expiresAt && (!isTokenExpired(expiresAt) || refresh),
  );
}

function buildRedirectUrl() {
  if (typeof window === "undefined") return "/login";
  const currentPath = `${window.location.pathname}${window.location.search}`;
  if (window.location.pathname === "/login") return "/login";
  return `/login?redirect=${encodeURIComponent(currentPath)}`;
}

export function redirectToLogin() {
  clearTokens();
  if (typeof unauthorizedHandler === "function") {
    unauthorizedHandler();
  }
}

function handleUnauthorized() {
  redirectToLogin();
}

async function parseResponsePayload(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function collectValidationErrors(payload) {
  if (!payload || typeof payload !== "object") return {};
  const rawDetails =
    payload.error?.details || payload.detail || payload.details;
  const details = Array.isArray(rawDetails) ? rawDetails : [];

  return details.reduce((acc, item) => {
    const loc = Array.isArray(item?.loc) ? item.loc : [];
    const field = item?.field || loc[loc.length - 1] || "form";
    acc[field] = item?.msg || item?.message || "Некорректное значение";
    return acc;
  }, {});
}

function detailsToMessage(details) {
  if (!details) return "";
  if (typeof details === "string") return details.trim();
  if (Array.isArray(details)) {
    return details
      .map((item) => {
        if (typeof item === "string") return item;
        const loc = Array.isArray(item?.loc) ? item.loc.join(".") : item?.field;
        const text = item?.msg || item?.message;
        return [loc, text].filter(Boolean).join(": ");
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof details === "object") {
    return Object.entries(details)
      .map(([field, value]) => {
        if (Array.isArray(value)) return `${field}: ${value.join(", ")}`;
        if (value && typeof value === "object")
          return `${field}: ${JSON.stringify(value)}`;
        return `${field}: ${value}`;
      })
      .join("; ");
  }
  return "";
}

async function createApiError(response, fallbackMessage) {
  const payload = await parseResponsePayload(response).catch(() => null);
  const apiError =
    payload && typeof payload === "object" ? payload.error : null;
  const detail = typeof payload === "object" ? payload?.detail : payload;
  const detailsMessage = detailsToMessage(
    apiError?.details || payload?.details || payload?.detail,
  );
  const statusMessages = {
    400: "Некорректный запрос.",
    401: "Необходимо войти заново.",
    403: "Недостаточно прав для выполнения действия.",
    404: "Запрошенные данные не найдены.",
    413: "Файл слишком большой.",
    422: "Проверьте корректность заполнения полей.",
    429: "Слишком много запросов. Подождите и попробуйте снова.",
    500: "Сервис временно недоступен. Попробуйте позже.",
  };
  const message =
    (typeof apiError?.public_message === "string" &&
      apiError.public_message.trim()) ||
    (typeof apiError?.message === "string" && apiError.message.trim()) ||
    (typeof detail === "string" && detail.trim()) ||
    detailsMessage ||
    statusMessages[response.status] ||
    fallbackMessage;

  return new ApiError(message, {
    status: apiError?.status || response.status,
    code: apiError?.code,
    validationErrors:
      response.status === 422 ? collectValidationErrors(payload) : {},
    payload,
  });
}

async function postRefreshToken(refresh, body) {
  return fetch(`${API_BASE}/auth/token/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function refreshAccessToken() {
  const { refresh } = getTokens();
  if (!refresh) return null;

  if (!refreshPromise) {
    refreshPromise = postRefreshToken(refresh, refresh)
      .then(async (response) => {
        if (!response.ok && [400, 422].includes(response.status)) {
          response = await postRefreshToken(refresh, {
            refresh_token: refresh,
          });
        }

        if (!response.ok) {
          throw await createApiError(response, "Сессия истекла.");
        }

        const data = await response.json();
        const session = saveTokensFromResponse(data);
        return session.accessToken;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

async function requestJson(
  path,
  options = {},
  { auth = true, retry = true, clearOnUnauthorized = true } = {},
) {
  const response = await apiFetch(path, options, {
    auth,
    retry,
    clearOnUnauthorized,
  });
  if (!response.ok) {
    throw await createApiError(
      response,
      `Ошибка запроса ${options.method || "GET"} ${path}`,
    );
  }
  if (response.status === 204) return null;

  const text = await response.text();
  if (!text.trim()) return null;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function login(credentialsOrEmail, maybePassword) {
  const credentials =
    typeof credentialsOrEmail === "object"
      ? credentialsOrEmail
      : { email: credentialsOrEmail, password: maybePassword };

  return requestJson(
    "/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: credentials.email,
        password: credentials.password,
      }),
    },
    { auth: false },
  );
}

export async function authenticateWithMembership(body) {
  return requestJson(
    "/auth/token",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    { auth: false },
  );
}

export async function logout(tokens) {
  return requestJson(
    "/auth/logout",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tokens),
    },
    { auth: false, retry: false },
  );
}

export async function apiFetch(
  path,
  options = {},
  { auth = true, retry = true, clearOnUnauthorized = true } = {},
) {
  const url = `${API_BASE}${path}`;
  const headers = { ...options.headers };
  let { access, expiresAt } = getTokens();

  if (auth && !access) {
    if (clearOnUnauthorized) {
      handleUnauthorized();
    }
    return new Response(null, { status: 401 });
  }

  if (auth && access && shouldRefresh(expiresAt)) {
    try {
      access = await refreshAccessToken();
    } catch {
      handleUnauthorized();
      return new Response(null, { status: 401 });
    }
  }

  if (auth && access) {
    headers.Authorization = `Bearer ${access}`;
  }

  let response = await fetch(url, { ...options, headers });

  if (auth && retry && response.status === 401 && access) {
    try {
      const newToken = await refreshAccessToken();
      if (newToken) {
        response = await fetch(url, {
          ...options,
          headers: { ...headers, Authorization: `Bearer ${newToken}` },
        });
      }
    } catch {
      handleUnauthorized();
      return response;
    }
  }

  if (auth && response.status === 401 && clearOnUnauthorized) {
    handleUnauthorized();
  }

  return response;
}

export async function fetchIdentity() {
  return requestJson("/auth/identity");
}

export async function acceptInvitation({
  token,
  password,
  full_name,
  username,
}) {
  const query = new URLSearchParams({ token });
  return requestJson(
    `/invitations/accept?${query.toString()}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password, full_name, username }),
    },
    { auth: false },
  );
}

// Внутренний системный метод: /permissions не должен иметь пользовательского экрана.
// Он предназначен только для служебной загрузки справочника прав и условного
// рендера функциональности админских интерфейсов, если такой UI появится.
export async function fetchPermissions(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => query.append(key, item));
    } else if (value !== undefined && value !== null && value !== "") {
      query.append(key, value);
    }
  });

  return requestJson(
    `/permissions${query.toString() ? `?${query.toString()}` : ""}`,
  );
}

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.append(key, value);
    }
  });
  return query.toString();
}

function normalizeOrganizationPage(response) {
  return {
    page: response?.page || 1,
    size: response?.size || 10,
    total_items: response?.total_items ?? response?.total ?? 0,
    total_pages: response?.total_pages ?? response?.pages ?? 1,
    has_next: Boolean(response?.has_next),
    has_prev: Boolean(response?.has_prev),
    items: Array.isArray(response?.items) ? response.items : [],
  };
}

function normalizeModelsPage(response) {
  const totalItems = response?.total_items ?? response?.total ?? 0;
  const size = response?.size || 10;

  return {
    page: response?.page || 1,
    size,
    total_items: totalItems,
    total: totalItems,
    total_pages:
      response?.total_pages ??
      response?.pages ??
      Math.max(1, Math.ceil(totalItems / size)),
    has_next: Boolean(response?.has_next),
    has_prev: Boolean(response?.has_prev),
    items: Array.isArray(response?.items) ? response.items : [],
  };
}

function sanitizeModelPayload(data = {}) {
  return {
    name: typeof data.name === "string" ? data.name.trim() : "",
    description: data.description || "",
    context: data.context || "",
  };
}

function sanitizeOrganizationPayload(data = {}, { partial = false } = {}) {
  const payload = {
    name: data.name,
    email: data.email,
    description: data.description,
  };

  if (!partial) return payload;

  return Object.fromEntries(
    Object.entries(payload).filter(
      ([, value]) => value !== undefined && value !== null && value !== "",
    ),
  );
}

export async function fetchOrganizationsPage(params = {}) {
  const query = buildQuery(params);
  const response = await requestJson(
    `/organizations${query ? `?${query}` : ""}`,
  );
  return normalizeOrganizationPage(response);
}

export async function fetchOrganizationById(organizationId) {
  return requestJson(`/organizations/${encodeURIComponent(organizationId)}`);
}

export async function createOrganization(data) {
  return requestJson("/organizations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sanitizeOrganizationPayload(data)),
  });
}

export async function updateOrganization(organizationId, data) {
  return requestJson(`/organizations/${encodeURIComponent(organizationId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sanitizeOrganizationPayload(data, { partial: true })),
  });
}

export async function deleteOrganization(organizationId) {
  return requestJson(`/organizations/${encodeURIComponent(organizationId)}`, {
    method: "DELETE",
  });
}

export async function fetchModelsPage(params = {}) {
  const response = await requestJson("/ai/models/get", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      page: params.page || 1,
      size: params.size || 10,
    }),
  });
  return normalizeModelsPage(response);
}

export async function createModel(data) {
  return requestJson("/ai/models/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sanitizeModelPayload(data)),
  });
}

export async function deleteModel(modelUid) {
  return requestJson(`/ai/models/${encodeURIComponent(modelUid)}`, {
    method: "DELETE",
  });
}

export async function fetchCurrentUser() {
  return requestJson("/users/me", {}, { clearOnUnauthorized: false });
}

export async function updateCurrentUser(changes) {
  return requestJson("/users/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
}

export async function fetchUsers(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "")
      query.append(key, value);
  });
  return requestJson(`/users${query.toString() ? `?${query.toString()}` : ""}`);
}

export async function fetchUserById(userId) {
  return requestJson(`/users/${encodeURIComponent(userId)}`);
}

export async function fetchRoleById() {
  throw new ApiError(
    "Роут /roles/{role_id} пока не подключён на backend и возвращает 404.",
    {
      status: 404,
    },
  );
}

export async function updateRoleById() {
  throw new ApiError(
    "Роут /roles/{role_id} пока не подключён на backend и возвращает 404.",
    {
      status: 404,
    },
  );
}

export const DOCUMENT_MAX_SIZE_BYTES = 30 * 1024 * 1024;
export const DOCUMENT_ALLOWED_EXTENSION =
  /\.(pdf|docx|pptx|xlsx|md|html|txt|json)$/i;
export const DOCUMENT_ALLOWED_EXTENSIONS_LABEL =
  ".pdf, .docx, .pptx, .xlsx, .md, .html, .txt и .json";

function validateDocumentFile(file) {
  if (!file) {
    throw new ApiError("Выберите файл для загрузки.", { status: 400 });
  }
  if (!DOCUMENT_ALLOWED_EXTENSION.test(file.name || "")) {
    throw new ApiError(
      `Поддерживаются файлы ${DOCUMENT_ALLOWED_EXTENSIONS_LABEL}.`,
      { status: 400 },
    );
  }
  if (file.size > DOCUMENT_MAX_SIZE_BYTES) {
    throw new ApiError("Размер файла не должен превышать 30 МБ.", {
      status: 413,
    });
  }
}

async function sendDocument(path, file) {
  validateDocumentFile(file);
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(path, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw await createApiError(response, "Ошибка загрузки документа");
  }

  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json")
    ? response.json()
    : response.text();
}

export async function uploadDocument(file) {
  return sendDocument("/documents/to/markdown", file);
}

export async function convertDocumentToMarkdown(file) {
  return sendDocument("/documents/to/markdown", file);
}

export async function saveDocument(file) {
  return sendDocument("/documents/upload", file);
}

// ─────────────────────────────────────────────────────────────
// Courses API: documented read/update endpoints and frontend mappers
// ─────────────────────────────────────────────────────────────

const DIFFICULTY_TO_LEVEL = {
  beginner: "Новичок",
  intermediate: "Средний",
  advanced: "Продвинутый",
  expert: "Эксперт",
};

const LEVEL_TO_DIFFICULTY = {
  Новичок: "beginner",
  Средний: "intermediate",
  Продвинутый: "advanced",
  Эксперт: "expert",
};

export function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    String(value || ""),
  );
}

export function courseLevelToDifficulty(level) {
  return LEVEL_TO_DIFFICULTY[level] || "beginner";
}

export function difficultyToCourseLevel(difficulty) {
  return DIFFICULTY_TO_LEVEL[difficulty] || "Новичок";
}

function parseMinutes(value) {
  const match = /(\d+)/.exec(String(value || ""));
  return match ? Number(match[1]) : null;
}

function contentBlockToMarkdown(block) {
  if (!block || typeof block !== "object") return "";

  if (block.content_type === "text") return block.md_content || "";
  if (block.content_type === "video") {
    return [block.url ? `[Видео](${block.url})` : "", block.description]
      .filter(Boolean)
      .join("\n\n");
  }
  if (block.content_type === "image")
    return block.image_id ? `Изображение: ${block.image_id}` : "";
  if (block.content_type === "program_code") {
    return [
      `\`\`\`${block.language || "text"}\n${block.code || ""}\n\`\`\``,
      block.explanation,
    ]
      .filter(Boolean)
      .join("\n\n");
  }
  if (block.content_type === "mermaid") {
    return [
      block.title ? `### ${block.title}` : "",
      `\`\`\`mermaid\n${block.md_content || ""}\n\`\`\``,
      block.explanation,
    ]
      .filter(Boolean)
      .join("\n\n");
  }
  if (block.content_type === "quiz") {
    return (block.questions || [])
      .map((question, index) => {
        const title = question?.question || `Вопрос ${index + 1}`;
        return [`${index + 1}. **${title}**`, question?.answer]
          .filter(Boolean)
          .join("\n\n");
      })
      .join("\n\n");
  }
  return [block.formula, block.explanation].filter(Boolean).join("\n\n");
}

function lessonMarkdownFromBlocks(contentBlocks) {
  return (contentBlocks || [])
    .map(contentBlockToMarkdown)
    .filter(Boolean)
    .join("\n\n---\n\n");
}

const SUPPORTED_CONTENT_TYPES = new Set([
  "text",
  "video",
  "image",
  "program_code",
  "mermaid",
  "quiz",
  "math_formula",
  "chemical_formula",
  "musical_notation",
]);

function withoutEmptyValues(payload) {
  return Object.fromEntries(
    Object.entries(payload).filter(
      ([, value]) => value !== undefined && value !== null,
    ),
  );
}

function sanitizeContentBlock(block) {
  const source =
    block && typeof block === "object" ? block : { content: block };
  const contentType = normalizeContentType(source);
  if (!SUPPORTED_CONTENT_TYPES.has(contentType)) {
    return {
      content_type: "text",
      ai_generated:
        typeof source.ai_generated === "boolean" ? source.ai_generated : false,
      md_content: String(source.md_content ?? source.content ?? block ?? ""),
    };
  }

  const payload = withoutEmptyValues({
    ...source,
    id: undefined,
    type: undefined,
    contentType: undefined,
    block_type: undefined,
    content_type: contentType,
    ai_generated:
      typeof source.ai_generated === "boolean" ? source.ai_generated : false,
  });

  if (contentType === "text") {
    payload.md_content =
      source.md_content ??
      source.mdContent ??
      source.markdown ??
      source.text ??
      source.content ??
      "";
  } else if (contentType === "image") {
    payload.image_id = getMediaId(
      source.image_id ??
        source.imageId ??
        source.image_url ??
        source.imageUrl ??
        source.url ??
        "",
    );
    delete payload.image_url;
    delete payload.imageUrl;
  } else if (contentType === "video") {
    payload.url = source.url ?? "";
    payload.description = source.description ?? "";
  } else if (contentType === "program_code") {
    payload.language = source.language ?? "text";
    payload.code = source.code ?? "";
    payload.explanation = source.explanation ?? "";
  } else if (contentType === "mermaid") {
    payload.title = source.title ?? "";
    payload.md_content =
      source.md_content ?? source.mdContent ?? source.content ?? "";
    payload.explanation = source.explanation ?? "";
  } else if (contentType === "quiz") {
    payload.questions = Array.isArray(source.questions)
      ? source.questions.map((question) => ({
          question: question?.question || "",
          answer: question?.answer || "",
        }))
      : [];
  } else {
    payload.formula = source.formula ?? "";
    payload.explanation = source.explanation ?? "";
  }

  return payload;
}

function blocksToPayload(blocks) {
  return (blocks || []).map((block) => ({
    title: block.title || "",
    description: block.description || "",
    duration: block.duration || "",
    learning_objectives: block.learningObjectives || [],
    lessons: (block.lessons || []).map((lesson) => ({
      title: lesson.title || "",
      description: lesson.summary || "",
      estimated_time_minutes: parseMinutes(lesson.duration),
      learning_objectives: [],
      content_blocks: lesson.contentBlocks
        ? lesson.contentBlocks.map(sanitizeContentBlock)
        : lesson.markdown
          ? [
              {
                content_type: "text",
                md_content: lesson.markdown,
                ai_generated: false,
              },
            ]
          : [],
    })),
  }));
}

export function buildCoursePayload(course) {
  return {
    title: course.title || "Новый курс",
    description: course.description || "",
    difficulty: courseLevelToDifficulty(course.level),
    category: course.category || "",
    duration: course.duration || "",
    format: course.format || "",
    learning_objectives: course.learningObjectives || [],
    tags: course.tags || [],
    modules: blocksToPayload(course.blocks),
  };
}

function readCourseModules(data) {
  const modules =
    data?.modules ||
    data?.course_modules ||
    data?.courseModules ||
    data?.module_ids ||
    data?.moduleIds ||
    data?.modules_ids ||
    data?.moduleIdsList ||
    [];

  return Array.isArray(modules) ? modules : [];
}

function getModuleId(data, fallbackId) {
  if (!data || typeof data !== "object") {
    return fallbackId;
  }

  return (
    data.module_id ||
    data.moduleId ||
    data.module_uuid ||
    data.moduleUuid ||
    data.uuid ||
    data.module?.id ||
    data.module?.module_id ||
    data.module?.moduleId ||
    data.data?.module_id ||
    data.data?.moduleId ||
    data.data?.id ||
    data.id ||
    fallbackId
  );
}

function normalizeModuleRef(module) {
  if (typeof module === "string") {
    return { id: module };
  }

  if (module?.module) {
    return normalizeModuleRef(module.module);
  }

  const id = getModuleId(module);
  return {
    ...module,
    id,
  };
}

function readModuleLessons(data) {
  const lessons =
    data?.lessons ||
    data?.module_lessons ||
    data?.moduleLessons ||
    data?.lesson_ids ||
    data?.lessonIds ||
    data?.lessons_ids ||
    [];

  return Array.isArray(lessons) ? lessons : [];
}

function normalizeLessonRef(lesson) {
  if (typeof lesson === "string") {
    return { id: lesson };
  }

  if (lesson?.lesson) {
    return normalizeLessonRef(lesson.lesson);
  }

  const id = lesson?.id || lesson?.lesson_id || lesson?.lessonId;
  return {
    ...lesson,
    id,
  };
}

function normalizeContentType(block) {
  const rawType = String(
    block?.content_type ||
      block?.contentType ||
      block?.block_type ||
      block?.type ||
      "text",
  ).toLowerCase();
  const aliases = {
    markdown: "text",
    md: "text",
    theory: "text",
    lecture: "text",
    code: "program_code",
    program: "program_code",
    diagram: "mermaid",
    question: "quiz",
    questions: "quiz",
    test: "quiz",
  };

  return aliases[rawType] || rawType;
}

function normalizeContentBlock(block) {
  const source =
    block && typeof block === "object" ? block : { content: block };
  const contentType = normalizeContentType(source);
  const normalized = {
    ...source,
    content_type: contentType,
    ai_generated:
      typeof source.ai_generated === "boolean" ? source.ai_generated : false,
  };

  if (contentType === "text") {
    normalized.md_content = String(
      source.md_content ??
        source.mdContent ??
        source.markdown ??
        source.text ??
        source.content ??
        source.theory ??
        "",
    );
  } else if (contentType === "image") {
    normalized.image_id = getMediaId(
      source.image_id ??
        source.imageId ??
        source.image_url ??
        source.imageUrl ??
        source.url ??
        source.src ??
        "",
    );
  } else if (contentType === "program_code") {
    normalized.language = String(source.language ?? source.lang ?? "text");
    normalized.code = String(source.code ?? source.content ?? "");
    normalized.explanation = String(
      source.explanation ?? source.description ?? "",
    );
  } else if (contentType === "mermaid") {
    normalized.md_content = String(
      source.md_content ??
        source.mdContent ??
        source.code ??
        source.content ??
        "",
    );
    normalized.explanation = String(
      source.explanation ?? source.description ?? "",
    );
  } else if (contentType === "quiz") {
    normalized.questions = Array.isArray(source.questions)
      ? source.questions
      : Array.isArray(source.items)
        ? source.items
        : [];
  }

  return normalized;
}

function readTheoryContentBlocks(data) {
  if (Array.isArray(data)) {
    return data;
  }
  if (!data || typeof data !== "object") {
    return null;
  }

  const directBlocks =
    data.content_blocks ||
    data.contentBlocks ||
    data.theory_blocks ||
    data.theoryBlocks ||
    data.blocks ||
    data.items ||
    data.results ||
    null;

  if (Array.isArray(directBlocks)) {
    return directBlocks;
  }

  const nestedSources = [
    data.data,
    data.lesson,
    data.lesson_theory,
    data.lessonTheory,
    data.theory,
    data.content,
  ];

  for (const source of nestedSources) {
    const nestedBlocks = readTheoryContentBlocks(source);
    if (Array.isArray(nestedBlocks)) {
      return nestedBlocks;
    }
  }

  return null;
}

function readTheoryMarkdown(data) {
  if (typeof data === "string") {
    return data;
  }
  if (!data || typeof data !== "object") {
    return "";
  }

  const markdown =
    data.markdown || data.md_content || data.mdContent || data.text || null;

  if (typeof markdown === "string") {
    return markdown;
  }
  if (typeof data.content === "string") {
    return data.content;
  }
  if (typeof data.theory === "string") {
    return data.theory;
  }

  const nestedSources = [
    data.data,
    data.lesson,
    data.lesson_theory,
    data.lessonTheory,
    data.theory,
    data.content,
  ];

  for (const source of nestedSources) {
    const nestedMarkdown = readTheoryMarkdown(source);
    if (nestedMarkdown) {
      return nestedMarkdown;
    }
  }

  return "";
}

function normalizeTheoryContentBlocks(data) {
  const rawBlocks = readTheoryContentBlocks(data);

  if (Array.isArray(rawBlocks)) {
    return rawBlocks.map(normalizeContentBlock).filter(Boolean);
  }

  const markdown = readTheoryMarkdown(data);

  return markdown
    ? [
        normalizeContentBlock({
          content_type: "text",
          ai_generated: false,
          md_content: markdown,
        }),
      ]
    : [];
}

export function mapCourseFromApi(data) {
  const blocks = readCourseModules(data).map((rawModule, moduleIndex) => {
    const module = normalizeModuleRef(rawModule);
    return {
      id: module.id,
      title: module.title || "Модуль без названия",
      description: module.description || "",
      order: Number.isFinite(module.order) ? module.order : moduleIndex,
      duration: module.duration || "Модуль курса",
      learningObjectives:
        module.learning_objectives || module.learningObjectives || [],
      learning_objectives:
        module.learning_objectives || module.learningObjectives || [],
      lessons: readModuleLessons(module).map((rawLesson, lessonIndex) => {
        const lesson = normalizeLessonRef(rawLesson);
        const contentBlocks = normalizeTheoryContentBlocks(
          lesson.content_blocks || lesson.contentBlocks || lesson.blocks || [],
        );
        return {
          id: lesson.id,
          title: lesson.title || "Урок без названия",
          duration: Number.isFinite(lesson.estimated_time_minutes)
            ? `${lesson.estimated_time_minutes} мин.`
            : "Материал урока",
          summary: lesson.description || "",
          description: lesson.description || "",
          content: lessonMarkdownFromBlocks(contentBlocks),
          markdown: lessonMarkdownFromBlocks(contentBlocks),
          contentBlocks,
          content_blocks: contentBlocks,
          order: Number.isFinite(lesson.order) ? lesson.order : lessonIndex,
          learningObjectives:
            lesson.learning_objectives || lesson.learningObjectives || [],
          learning_objectives:
            lesson.learning_objectives || lesson.learningObjectives || [],
        };
      }),
      practice: [],
    };
  });

  return {
    ...data,
    id: data.id,
    title: data.title || "",
    category: data.category || data.difficulty || "",
    description: data.description || "",
    duration: data.duration || "",
    level: difficultyToCourseLevel(data.difficulty),
    difficulty: data.difficulty || difficultyToCourseLevel(data.difficulty),
    format: data.format || "",
    tags: data.tags || [],
    learningObjectives:
      data.learning_objectives || data.learningObjectives || [],
    learning_objectives:
      data.learning_objectives || data.learningObjectives || [],
    blocks,
    modules: blocks,
  };
}

function courseChangesToPatch(changes) {
  const patch = {};
  if ("title" in changes) patch.title = changes.title;
  if ("description" in changes) patch.description = changes.description;
  if ("tags" in changes) patch.tags = changes.tags;
  if ("level" in changes)
    patch.difficulty = courseLevelToDifficulty(changes.level);
  if ("difficulty" in changes) patch.difficulty = changes.difficulty;
  return patch;
}

function moduleChangesToPatch(changes) {
  const patch = {};
  if ("title" in changes) patch.title = changes.title;
  if ("description" in changes) patch.description = changes.description;
  if ("order" in changes) patch.order = changes.order;
  if ("learningObjectives" in changes) {
    patch.learning_objectives = changes.learningObjectives;
  }
  if ("learning_objectives" in changes) {
    patch.learning_objectives = changes.learning_objectives;
  }
  return patch;
}

function lessonChangesToPatch(changes) {
  const patch = {};
  if ("title" in changes) patch.title = changes.title;
  if ("description" in changes) patch.description = changes.description;
  if ("summary" in changes) patch.description = changes.summary;
  if ("order" in changes) patch.order = changes.order;
  if ("learningObjectives" in changes) {
    patch.learning_objectives = changes.learningObjectives;
  }
  if ("learning_objectives" in changes) {
    patch.learning_objectives = changes.learning_objectives;
  }
  if ("estimatedTimeMinutes" in changes) {
    patch.estimated_time_minutes = changes.estimatedTimeMinutes;
  }
  if ("estimated_time_minutes" in changes) {
    patch.estimated_time_minutes = changes.estimated_time_minutes;
  }
  if ("duration" in changes)
    patch.estimated_time_minutes = parseMinutes(changes.duration);
  if ("contentBlocks" in changes) {
    patch.content_blocks = (changes.contentBlocks || []).map(
      sanitizeContentBlock,
    );
  } else if ("content_blocks" in changes) {
    patch.content_blocks = (changes.content_blocks || []).map(
      sanitizeContentBlock,
    );
  } else if ("markdown" in changes) {
    patch.content_blocks = changes.markdown
      ? [
          {
            content_type: "text",
            md_content: changes.markdown,
            ai_generated: false,
          },
        ]
      : [];
  }
  return patch;
}

async function jsonRequest(path, method, body, options = {}) {
  const { auth, retry, ...fetchOptions } = options;
  return requestJson(
    path,
    {
      ...fetchOptions,
      method,
      headers: {
        "Content-Type": "application/json",
        ...(fetchOptions.headers || {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    {
      auth: auth ?? true,
      retry: retry ?? true,
    },
  );
}

function courseBasicToLearningCourse(data) {
  const blocks = readCourseModules(data).map((rawModule, moduleIndex) => {
    const module = normalizeModuleRef(rawModule);
    return {
      id: module.id,
      title: module.title || "Модуль без названия",
      description: module.description || "",
      order: Number.isFinite(module.order) ? module.order : moduleIndex,
      duration: module.duration || "Модуль курса",
      learningObjectives:
        module.learning_objectives || module.learningObjectives || [],
      learning_objectives:
        module.learning_objectives || module.learningObjectives || [],
      lessons: readModuleLessons(module).map((lesson, lessonIndex) =>
        lessonBasicToLearningLesson(normalizeLessonRef(lesson), {
          order: lessonIndex,
        }),
      ),
      practice: [],
    };
  });

  return {
    ...data,
    category: data.category || data.difficulty || "Не указан",
    duration: data.duration || "По индивидуальному темпу",
    level: data.difficulty || "Не указан",
    difficulty: data.difficulty || data.level || "Не указан",
    format: data.format || "Теория + практика",
    learningObjectives:
      data.learning_objectives || data.learningObjectives || [],
    learning_objectives:
      data.learning_objectives || data.learningObjectives || [],
    blocks,
    modules: blocks,
  };
}

function moduleBasicToLearningBlock(data, currentBlock = {}) {
  if (typeof data === "string") {
    return {
      ...currentBlock,
      id: data,
      title: currentBlock.title || "Модуль без названия",
      description: currentBlock.description || "",
      order: currentBlock.order || 0,
      duration: currentBlock.duration || "Модуль курса",
      learningObjectives: currentBlock.learningObjectives || [],
      learning_objectives: currentBlock.learning_objectives || [],
      lessons: currentBlock.lessons || [],
      practice: currentBlock.practice || [],
    };
  }

  const learningObjectives =
    data.learning_objectives || data.learningObjectives || [];
  return {
    ...currentBlock,
    id: getModuleId(data, currentBlock.id),
    title: data.title || "Модуль без названия",
    description: data.description || "",
    order: Number.isFinite(data.order) ? data.order : currentBlock.order || 0,
    duration: data.duration || currentBlock.duration || "Модуль курса",
    learningObjectives,
    learning_objectives: learningObjectives,
    lessons: readModuleLessons(data).map((lesson, lessonIndex) =>
      lessonBasicToLearningLesson(normalizeLessonRef(lesson), {
        order: lessonIndex,
      }),
    ),
    practice: currentBlock.practice || [],
  };
}

function lessonBasicToLearningLesson(data, currentLesson = {}) {
  const contentBlocks = normalizeTheoryContentBlocks(
    data.content_blocks ||
      data.contentBlocks ||
      currentLesson.contentBlocks ||
      [],
  );
  const markdown = lessonMarkdownFromBlocks(contentBlocks);
  const learningObjectives =
    data.learning_objectives || data.learningObjectives || [];
  return {
    ...currentLesson,
    id: data.id,
    title: data.title || "Урок без названия",
    duration: Number.isFinite(data.estimated_time_minutes)
      ? `${data.estimated_time_minutes} мин.`
      : currentLesson.duration || "Время не указано",
    summary: data.description || "",
    description: data.description || "",
    content: markdown || data.description || currentLesson.content || "",
    markdown: markdown || currentLesson.markdown || "",
    contentBlocks,
    content_blocks: contentBlocks,
    order: Number.isFinite(data.order) ? data.order : currentLesson.order || 0,
    learningObjectives,
    learning_objectives: learningObjectives,
  };
}

function normalizePaginatedResponse(data, { page = 1, size = 20 } = {}) {
  const rawItems = Array.isArray(data)
    ? data
    : data?.items || data?.courses || data?.results || [];
  const items = rawItems.map((course) =>
    readCourseModules(course).length
      ? mapCourseFromApi(course)
      : courseBasicToLearningCourse(course),
  );
  const totalItems =
    Number(data?.total) ||
    Number(data?.total_items) ||
    Number(data?.count) ||
    (Array.isArray(data) ? data.length : items.length);
  const totalPages =
    Number(data?.total_pages) ||
    Number(data?.pages) ||
    Math.max(1, Math.ceil(totalItems / Math.max(1, size)));

  return {
    ...data,
    items,
    page: Number(data?.page) || page,
    size: Number(data?.size) || size,
    total: totalItems,
    total_pages: totalPages,
    pages: totalPages,
    has_next: Boolean(data?.has_next ?? data?.hasNext ?? page < totalPages),
    has_prev: Boolean(data?.has_prev ?? data?.hasPrev ?? page > 1),
  };
}

export async function fetchCoursesPage(
  { page = 1, size = 20 } = {},
  options = {},
) {
  const data = await jsonRequest(
    "/course/",
    "POST",
    { page, size },
    { ...options, auth: false },
  );
  return normalizePaginatedResponse(data, { page, size });
}

export async function fetchCourses(params = {}, options = {}) {
  const response = await fetchCoursesPage(params, options);
  return response.items;
}

export async function fetchMyCoursesPage(
  { page = 1, size = 10 } = {},
  options = {},
) {
  const data = await jsonRequest(
    "/course/my-courses",
    "POST",
    { page, size },
    options,
  );
  return normalizePaginatedResponse(data, { page, size });
}

export async function createCourse(data, options = {}) {
  const response = await jsonRequest(
    "/course/create",
    "POST",
    {
      title: data.title || "Новый курс",
      description: data.description || "",
      difficulty: data.difficulty || "beginner",
      status: data.status || "draft",
      tags: Array.isArray(data.tags) ? data.tags : [],
    },
    options,
  );
  return courseBasicToLearningCourse(response);
}

export async function getCourseBasicInfo(courseId, options = {}) {
  if (!isUuid(courseId)) {
    throw new ApiError("Некорректный идентификатор курса.", {
      status: 400,
      code: "invalid_course_id",
    });
  }

  const data = await requestJson(
    `/course/basic/info/${encodeURIComponent(courseId)}`,
    options,
    { auth: false },
  );
  return courseBasicToLearningCourse(data);
}

export async function getCourse(courseId, options = {}) {
  return getCourseBasicInfo(courseId, options);
}

export async function getModuleBasicInfo(moduleId, options = {}) {
  const data = await requestJson(
    `/module/basic/info/${encodeURIComponent(moduleId)}`,
    options,
    { auth: false },
  );
  return moduleBasicToLearningBlock(data);
}

export async function getLessonBasicInfo(lessonId, options = {}) {
  const data = await requestJson(
    `/lesson/basic/info/${encodeURIComponent(lessonId)}`,
    options,
  );
  return lessonBasicToLearningLesson(data);
}

export async function getLessonTheory(lessonId, options = {}) {
  const data = await requestJson(
    `/lesson/theory/${encodeURIComponent(lessonId)}`,
    options,
  );
  return normalizeTheoryContentBlocks(data);
}

export async function updateCourse(courseId, changes) {
  const patch = withoutEmptyValues(courseChangesToPatch(changes));
  if (!Object.keys(patch).length) return null;
  const data = await jsonRequest(
    `/course/edit/${encodeURIComponent(courseId)}`,
    "PUT",
    patch,
  );
  return data?.modules
    ? mapCourseFromApi(data)
    : courseBasicToLearningCourse(data);
}

export async function createModule(courseId, data, options = {}) {
  const query = courseId
    ? `?${new URLSearchParams({ course_id: courseId }).toString()}`
    : "";
  const payload = {
    title: data.title || "Новый модуль",
    description: data.description || "",
    order: Number.isFinite(data.order) ? data.order : 1,
    learning_objectives:
      data.learning_objectives || data.learningObjectives || [],
  };
  const response = await jsonRequest(
    `/module/create${query}`,
    "POST",
    payload,
    options,
  );

  const directModule = response?.module || response?.data?.module;
  const courseModules = [
    ...readCourseModules(response),
    ...readCourseModules(response?.data),
  ];
  const createdModule =
    directModule ||
    courseModules.find((module) => {
      const normalized = normalizeModuleRef(module);
      return (
        normalized.title === payload.title ||
        Number(normalized.order) === Number(payload.order)
      );
    }) ||
    courseModules.at(-1) ||
    response?.data ||
    response;

  return moduleBasicToLearningBlock(createdModule, {
    title: payload.title,
    description: payload.description,
    order: payload.order,
    learningObjectives: payload.learning_objectives,
    learning_objectives: payload.learning_objectives,
  });
}

export async function assignModuleToCourse(moduleId, courseId, options = {}) {
  return requestJson(
    `/module/assign/${encodeURIComponent(moduleId)}/${encodeURIComponent(courseId)}`,
    {
      method: "POST",
    },
    options,
  );
}

export async function createLesson(data, options = {}) {
  const moduleId = data.module_id || data.moduleId;
  const query = moduleId
    ? `?${new URLSearchParams({ module_id: moduleId }).toString()}`
    : "";
  const response = await jsonRequest(
    `/lesson/create${query}`,
    "POST",
    {
      title: data.title || "Новый урок",
      description: data.description || "",
      order: Number.isFinite(data.order) ? data.order : 1,
      learning_objectives:
        data.learning_objectives || data.learningObjectives || [],
      estimated_time_minutes:
        data.estimated_time_minutes ?? data.estimatedTimeMinutes ?? null,
    },
    options,
  );
  return lessonBasicToLearningLesson(
    normalizeLessonRef(response?.lesson || response),
    {
      title: data.title || "Новый урок",
      description: data.description || "",
      order: Number.isFinite(data.order) ? data.order : 1,
      learningObjectives:
        data.learning_objectives || data.learningObjectives || [],
      learning_objectives:
        data.learning_objectives || data.learningObjectives || [],
    },
  );
}

export async function assignLessonToModule(lessonId, moduleId, options = {}) {
  return requestJson(
    `/lesson/assign/${encodeURIComponent(lessonId)}/${encodeURIComponent(moduleId)}`,
    {
      method: "POST",
    },
    options,
  );
}

export async function updateModule(courseId, moduleId, changes) {
  const patch = withoutEmptyValues(moduleChangesToPatch(changes));
  if (!Object.keys(patch).length) return null;
  const data = await jsonRequest(
    `/module/edit/${encodeURIComponent(moduleId)}`,
    "PUT",
    patch,
  );
  return moduleBasicToLearningBlock(data);
}

export async function updateLesson(courseId, lessonId, changes) {
  if (
    "contentBlocks" in changes ||
    "content_blocks" in changes ||
    "markdown" in changes
  ) {
    const contentBlocks =
      "markdown" in changes
        ? lessonChangesToPatch(changes).content_blocks
        : changes.contentBlocks || changes.content_blocks || [];
    return updateLessonContentBlocks(lessonId, contentBlocks);
  }
  const patch = withoutEmptyValues(lessonChangesToPatch(changes));
  if (!Object.keys(patch).length) return null;
  const data = await jsonRequest(
    `/lesson/edit/${encodeURIComponent(lessonId)}`,
    "PUT",
    patch,
  );
  return lessonBasicToLearningLesson(data);
}

export async function updateLessonContentBlocks(lessonId, contentBlocks) {
  const payload = (Array.isArray(contentBlocks) ? contentBlocks : [])
    .map(sanitizeContentBlock)
    .filter(Boolean);
  const data = await jsonRequest(
    `/lesson/update/${encodeURIComponent(lessonId)}`,
    "PUT",
    payload,
  );
  return lessonBasicToLearningLesson({
    id: lessonId,
    content_blocks: payload,
    ...(data || {}),
  });
}

export async function deleteModule(moduleId, options = {}) {
  return requestJson(
    `/module/${encodeURIComponent(moduleId)}`,
    { method: "DELETE" },
    options,
  );
}

export async function deleteLesson(lessonId, options = {}) {
  return requestJson(
    `/lesson/${encodeURIComponent(lessonId)}`,
    { method: "DELETE" },
    options,
  );
}

function normalizeAgentResponse(data) {
  return {
    ...data,
    chatId: data?.chat_id || data?.chatId || null,
    content: data?.content ?? data?.response?.content ?? "",
  };
}

function extractCourseStatus(data) {
  if (typeof data === "string") return data;
  if (!data || typeof data !== "object") return "";
  return (
    data.status ||
    data.course_status ||
    data.courseStatus ||
    data.state ||
    Object.values(data).find((value) => typeof value === "string") ||
    ""
  );
}

export async function fetchCourseStatus(courseId, options = {}) {
  const data = await requestJson(
    `/course/${encodeURIComponent(courseId)}/status`,
    { method: "GET", ...(options || {}) },
  );
  return { raw: data, status: extractCourseStatus(data) };
}

export async function publishCourse(courseId, options = {}) {
  const data = await requestJson(
    `/course/publish/${encodeURIComponent(courseId)}`,
    { method: "POST", ...(options || {}) },
  );
  return { raw: data, status: extractCourseStatus(data) || "published" };
}

export async function setCourseInviteOnly(courseId, options = {}) {
  const data = await requestJson(
    `/course/${encodeURIComponent(courseId)}/invite-only`,
    { method: "POST", ...(options || {}) },
  );
  return { raw: data, status: extractCourseStatus(data) || "invite_only" };
}

export async function archiveCourse(courseId, options = {}) {
  const data = await requestJson(
    `/course/delete/${encodeURIComponent(courseId)}`,
    { method: "DELETE", ...(options || {}) },
  );
  return { raw: data, status: extractCourseStatus(data) || "archived" };
}

function normalizeCreatedPracticeResponse(data) {
  const practice = data?.practice || data?.assignment || data?.test || data;
  return {
    practice,
    practiceId: data?.practice_id || data?.practiceId || data?.id || null,
    raw: data,
  };
}

function appendPracticeAssignmentFormFields(formData, assignment = {}) {
  formData.append("practice", JSON.stringify(assignment));
}

export async function generateLessonTest(moduleId, lessonId, options = {}) {
  return normalizeCreatedPracticeResponse(
    await requestJson(
      `/agent/test/${encodeURIComponent(moduleId)}/${encodeURIComponent(lessonId)}`,
      { method: "POST", ...(options || {}) },
    ),
  );
}

export async function checkLessonTest(practiceId, payload, options = {}) {
  return jsonRequest(
    `/agent/check/test/${encodeURIComponent(practiceId)}`,
    "POST",
    payload,
    options,
  );
}

export async function generateLessonPractice(moduleId, lessonId, options = {}) {
  return normalizeCreatedPracticeResponse(
    await requestJson(
      `/agent/practice/${encodeURIComponent(moduleId)}/${encodeURIComponent(lessonId)}`,
      { method: "POST", ...(options || {}) },
    ),
  );
}

export async function checkLessonPractice(
  practiceId,
  assignment,
  file,
  options = {},
) {
  const formData = new FormData();
  appendPracticeAssignmentFormFields(formData, assignment);
  formData.append("file", file);

  const response = await apiFetch(
    `/agent/check/practice/${encodeURIComponent(practiceId)}`,
    { method: "POST", body: formData, ...(options || {}) },
  );

  if (!response.ok) {
    throw await createApiError(
      response,
      "Не удалось проверить практическое задание.",
    );
  }

  return response.json();
}

function toAgentChatPayload(payload = {}) {
  return withoutEmptyValues({
    chat_id: payload.chat_id || payload.chatId,
    course_id: payload.course_id || payload.courseId,
    role: payload.role || "user",
    content: payload.content ?? payload.message ?? payload.prompt ?? "",
  });
}

export async function askInterviewerAgent(payload, options = {}) {
  return normalizeAgentResponse(
    await jsonRequest(
      "/agent/interviewer",
      "POST",
      toAgentChatPayload(payload),
      options,
    ),
  );
}

export async function askMentorAgent(payload, options = {}) {
  return normalizeAgentResponse(
    await jsonRequest(
      "/agent/mentor",
      "POST",
      {
        ...toAgentChatPayload(payload),
        content_blocks: Array.isArray(payload.content_blocks)
          ? payload.content_blocks
          : [],
      },
      options,
    ),
  );
}

function normalizeSupportedContentType(value) {
  const contentType = normalizeContentType({ content_type: value || "text" });
  return SUPPORTED_CONTENT_TYPES.has(contentType) ? contentType : "text";
}

function normalizeEditorContentBlock(
  contentBlock,
  fallbackContentType = "text",
) {
  if (!contentBlock) return contentBlock;

  if (typeof contentBlock === "string") {
    try {
      const parsed = JSON.parse(contentBlock);
      return JSON.stringify({
        ...parsed,
        content_type: normalizeSupportedContentType(
          parsed?.content_type || fallbackContentType || "text",
        ),
        ai_generated:
          typeof parsed?.ai_generated === "boolean"
            ? parsed.ai_generated
            : false,
      });
    } catch {
      return JSON.stringify({
        content_type: normalizeSupportedContentType(fallbackContentType),
        ai_generated: false,
        md_content: contentBlock,
      });
    }
  }

  if (typeof contentBlock === "object") {
    return {
      ...contentBlock,
      content_type: normalizeSupportedContentType(
        contentBlock.content_type || fallbackContentType || "text",
      ),
      ai_generated:
        typeof contentBlock.ai_generated === "boolean"
          ? contentBlock.ai_generated
          : false,
    };
  }

  return contentBlock;
}

export async function askEditorAgent(payload = {}, options = {}) {
  const images = Array.isArray(payload.images)
    ? payload.images.filter(Boolean).slice(0, 3)
    : [];
  const contentType = normalizeSupportedContentType(payload.content_type);
  const requestPayload = withoutEmptyValues({
    ...toAgentChatPayload(payload),
    content_type: contentType,
    content_block: normalizeEditorContentBlock(
      payload.content_block,
      contentType,
    ),
    content_blocks: Array.isArray(payload.content_blocks)
      ? payload.content_blocks.map(sanitizeContentBlock)
      : [],
    images: images.length > 0 ? images : undefined,
  });
  const data = await jsonRequest(
    "/agent/editor",
    "POST",
    requestPayload,
    options,
  );
  console.log("[/agent/editor] response", data);

  const content = data?.content;
  let parsedContent = null;
  if (typeof content === "string" && content.trim()) {
    try {
      parsedContent = JSON.parse(content);
    } catch {
      parsedContent = null;
    }
  }
  return { ...normalizeAgentResponse(data), parsedContent };
}
