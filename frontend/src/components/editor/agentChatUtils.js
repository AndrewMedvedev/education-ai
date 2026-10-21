// Общие помощники для диалогов с ИИ-интервьюерами (курс, модуль, урок).

// Агент после показа структуры явно спрашивает, подтверждает ли пользователь запуск.
const ASKS_CONFIRMATION =
  /(подтвержда\p{L}*|подтверди\p{L}*|подтверждени\p{L}*|запуска\p{L}* генерац|запуск\p{L}* генерац|запустить генерац|можно запускать|запускаем\??)/iu;

// Короткие ответы-согласия, которые агент примет как подтверждение запуска.
const USER_CONFIRMS =
  /^\s*(да|ага|ок|окей|ok|okay|go|подтвержда\p{L}*|подтверди\p{L}*|запуска\p{L}*|запусти\p{L}*|генерируй\p{L}*|согла\p{L}*|верно|все верно|всё верно|давай\p{L}*|поехали|старт)(?=$|[\s.,!?;:)…])/iu;

// Ответ с правками — это не подтверждение, его отправляем агенту как обычное сообщение.
const USER_ASKS_CHANGES =
  /(^|[\s,])(но|однако|кроме|только)(?=[\s,])|измен|поменя|добав|убер|убра|замен|исправ|передела|не\s/iu;

export const CONFIRM_LAUNCH_MESSAGE =
  "Подтверждаю эту версию. Запускай генерацию.";

export function getLastAssistantMessage(messages = []) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index]?.role === "assistant") return messages[index];
  }
  return null;
}

/** Ждёт ли агент подтверждения запуска (последнее слово за агентом и он спрашивает). */
export function isAwaitingLaunchConfirmation(messages = []) {
  const last = messages[messages.length - 1];
  if (!last || last.role !== "assistant") return false;
  return ASKS_CONFIRMATION.test(String(last.text || ""));
}

export function looksLikeLaunchConfirmation(text) {
  const value = String(text || "").trim();
  return (
    value.length <= 120 &&
    USER_CONFIRMS.test(value) &&
    !USER_ASKS_CHANGES.test(value)
  );
}

function parseMaybeJson(value) {
  if (typeof value !== "string") return value;
  const trimmed = value.trim();
  if (!/^[{[]/.test(trimmed)) return value;
  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
}

/** task_id из ответа интервьюера: после запуска backend кладёт в content { task_id }. */
export function extractTaskId(response) {
  const content = parseMaybeJson(response?.content);
  if (content && typeof content === "object") {
    return content.task_id || content.taskId || null;
  }
  const match = String(content || "").match(/task_id\s*[=:]\s*([\w-]+)/i);
  return match ? match[1] : null;
}

/** Текст ответа для истории; объект с task_id превращаем в понятную фразу. */
export function getResponseText(response, startedText) {
  const content = parseMaybeJson(response?.content);
  if (content && typeof content === "object") {
    return content.task_id || content.taskId ? startedText : "";
  }
  return String(content || "").trim();
}

export function safeLinkHref(href) {
  const value = String(href || "").trim();
  if (/^https?:\/\//i.test(value) || /^mailto:/i.test(value)) return value;
  return null;
}
