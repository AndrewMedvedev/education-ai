import { ApiError, apiFetch } from "./api";

// Настраиваемый frontend-лимит до сетевых запросов. Если backend/product зададут
// другой лимит, поменяйте значение здесь и/или вынесите его в VITE_MAX_FILE_SIZE_BYTES.
export const MAX_FILE_SIZE_BYTES =
  Number(import.meta.env.VITE_MAX_FILE_SIZE_BYTES) || 25 * 1024 * 1024;
export const PRESIGNED_URL_TTL_SECONDS = 1800;

const CONTENT_TYPE_RE = /^[\w-]+\/[\w-.]+$/;
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const FALLBACK_CONTENT_TYPE = "application/octet-stream";

// Бизнес-allowlist в проекте не задан. Поэтому используем denylist опасных
// исполняемых/скриптовых расширений и оставляем MIME-types расширяемыми через options.
export const BLOCKED_FILE_EXTENSIONS = new Set([
  "ade",
  "adp",
  "apk",
  "app",
  "bat",
  "bin",
  "cmd",
  "com",
  "cpl",
  "dll",
  "dmg",
  "exe",
  "gadget",
  "hta",
  "html",
  "iso",
  "jar",
  "js",
  "jse",
  "ksh",
  "lnk",
  "msi",
  "msp",
  "pif",
  "ps1",
  "scr",
  "sh",
  "vb",
  "vbe",
  "vbs",
  "wsf",
]);

export class AttachmentError extends ApiError {
  constructor(message, { status, code, step, fileName, payload } = {}) {
    super(message, { status, code, payload });
    this.name = "AttachmentError";
    this.step = step;
    this.fileName = fileName;
  }
}

function normalizeFilename(filename) {
  return String(filename || "").trim();
}

function getExtension(filename) {
  const normalized = normalizeFilename(filename).toLowerCase();
  const index = normalized.lastIndexOf(".");
  return index >= 0 ? normalized.slice(index + 1) : "";
}

export function getUploadContentType(file) {
  const contentType =
    String(file?.type || FALLBACK_CONTENT_TYPE).trim() || FALLBACK_CONTENT_TYPE;
  return CONTENT_TYPE_RE.test(contentType)
    ? contentType
    : FALLBACK_CONTENT_TYPE;
}

export function validateAttachmentFile(file, options = {}) {
  const {
    maxSizeBytes = MAX_FILE_SIZE_BYTES,
    allowedMimeTypes,
    blockedExtensions = BLOCKED_FILE_EXTENSIONS,
  } = options;

  if (!file) {
    throw new AttachmentError("Выберите файл для загрузки.", {
      code: "FILE_REQUIRED",
      step: "validation",
    });
  }

  const filename = normalizeFilename(file.name);
  if (!filename) {
    throw new AttachmentError("Имя файла не должно быть пустым.", {
      code: "INVALID_FILENAME",
      step: "validation",
    });
  }

  if (filename.length > 255) {
    throw new AttachmentError("Имя файла не должно превышать 255 символов.", {
      code: "FILENAME_TOO_LONG",
      step: "validation",
      fileName: filename,
    });
  }

  if (Number(file.size) > maxSizeBytes) {
    throw new AttachmentError(
      `Файл больше допустимого лимита ${formatFileSize(maxSizeBytes)}.`,
      {
        code: "FILE_TOO_LARGE",
        step: "validation",
        fileName: filename,
      },
    );
  }

  const extension = getExtension(filename);
  if (extension && blockedExtensions.has(extension)) {
    throw new AttachmentError(
      "Этот тип файла запрещён для загрузки из соображений безопасности.",
      {
        code: "BLOCKED_EXTENSION",
        step: "validation",
        fileName: filename,
      },
    );
  }

  const contentType = getUploadContentType(file);
  if (allowedMimeTypes && !allowedMimeTypes.has(contentType)) {
    throw new AttachmentError("Этот MIME-тип файла не разрешён для загрузки.", {
      code: "BLOCKED_MIME_TYPE",
      step: "validation",
      fileName: filename,
    });
  }

  return { filename, contentType };
}

function validateOwnerId(ownerId) {
  if (!UUID_RE.test(String(ownerId || ""))) {
    throw new AttachmentError(
      "Некорректный идентификатор сущности для вложения.",
      {
        status: 422,
        code: "INVALID_OWNER_ID",
        step: "validation",
      },
    );
  }
}

function formatFileSize(bytes) {
  if (bytes >= 1024 * 1024) return `${Math.round(bytes / 1024 / 1024)} МБ`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} КБ`;
  return `${bytes} Б`;
}

async function readPayload(response) {
  const contentType = response.headers.get("content-type") || "";
  try {
    return contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  } catch {
    return null;
  }
}

function messageForStatus(step, status) {
  if (step === "presigned-upload") {
    if (status === 422) return "Некорректное имя или тип файла.";
    if (status === 500)
      return "Хранилище временно недоступно. Попробуйте повторить загрузку.";
  }

  if (step === "confirm-upload") {
    if (status === 401) return "Необходимо войти заново.";
    if (status === 404)
      return "Файл не был найден в хранилище. Попробуйте загрузить его заново.";
    if ([400, 409, 422].includes(status))
      return "Ошибка проверки данных вложения.";
    if (status === 500)
      return "Не удалось сохранить сведения о файле. Попробуйте повторить загрузку.";
  }

  if (step === "presigned-download" || step === "get-attachment") {
    if (status === 404) return "Файл не найден или был удалён.";
    if (status === 422) return "Некорректный идентификатор файла.";
    if (status === 500) return "Не удалось получить файл из хранилища.";
  }

  if (step === "storage-put") {
    return "Не удалось загрузить файл в хранилище. Повторите попытку для этого файла.";
  }

  if (step === "storage-download") {
    return "Не удалось скачать файл из хранилища.";
  }

  return "Не удалось выполнить операцию с файлом.";
}

async function throwAttachmentResponseError(response, step, fileName) {
  const payload = await readPayload(response);
  throw new AttachmentError(messageForStatus(step, response.status), {
    status: response.status,
    code: `${step.toUpperCase().replace(/-/g, "_")}_${response.status}`,
    step,
    fileName,
    payload,
  });
}

function rewriteStorageUrl(url) {
  const publicHost = String(
    import.meta.env.VITE_STORAGE_PUBLIC_HOST || "",
  ).trim();
  if (!publicHost) return url;

  try {
    const rewritten = new URL(url);
    const publicUrl = publicHost.includes("://")
      ? new URL(publicHost)
      : new URL(`${rewritten.protocol}//${publicHost}`);
    const publicPath = publicUrl.pathname.replace(/\/+$/, "");

    rewritten.protocol = publicUrl.protocol;
    rewritten.host = publicUrl.host;

    if (
      publicPath &&
      publicPath !== "/" &&
      !rewritten.pathname.startsWith(`${publicPath}/`)
    ) {
      rewritten.pathname = `${publicPath}${rewritten.pathname.startsWith("/") ? "" : "/"}${rewritten.pathname}`;
    }

    return rewritten.toString();
  } catch {
    return url;
  }
}

async function requestJson(
  path,
  options,
  { auth = true, step, fileName } = {},
) {
  let response;
  try {
    response = await apiFetch(path, options, { auth });
  } catch (error) {
    throw new AttachmentError(
      "Сеть недоступна. Проверьте подключение и повторите попытку.",
      {
        code: "NETWORK_ERROR",
        step,
        fileName,
        payload: error,
      },
    );
  }

  if (!response.ok) {
    await throwAttachmentResponseError(response, step, fileName);
  }

  return response.json();
}

async function putFileToStorage(uploadUrl, file, { signal } = {}) {
  const publicUrl = rewriteStorageUrl(uploadUrl);
  try {
    const response = await fetch(publicUrl, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": getUploadContentType(file) },
      signal,
    });

    if (!response.ok) {
      await throwAttachmentResponseError(response, "storage-put", file.name);
    }
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new AttachmentError("Загрузка файла отменена.", {
        code: "UPLOAD_ABORTED",
        step: "storage-put",
        fileName: file.name,
      });
    }

    if (error instanceof AttachmentError) throw error;

    throw new AttachmentError(
      "Не удалось загрузить файл в хранилище. Повторите попытку для этого файла.",
      {
        code: "STORAGE_NETWORK_ERROR",
        step: "storage-put",
        fileName: file.name,
        payload: error,
      },
    );
  }
}

async function fetchBlobFromStorage(downloadUrl, { signal } = {}) {
  const publicUrl = rewriteStorageUrl(downloadUrl);
  let response;
  try {
    response = await fetch(publicUrl, { signal });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new AttachmentError("Скачивание файла отменено.", {
        code: "DOWNLOAD_ABORTED",
        step: "storage-download",
      });
    }
    throw new AttachmentError("Не удалось скачать файл из хранилища.", {
      code: "STORAGE_DOWNLOAD_NETWORK_ERROR",
      step: "storage-download",
      payload: error,
    });
  }

  if (!response.ok) {
    await throwAttachmentResponseError(response, "storage-download");
  }

  return response.blob();
}

export async function runWithConcurrency(
  items,
  worker,
  { concurrency = 3 } = {},
) {
  const results = new Array(items.length);
  let nextIndex = 0;

  async function runNext() {
    const index = nextIndex;
    nextIndex += 1;
    if (index >= items.length) return;

    try {
      results[index] = {
        status: "success",
        value: await worker(items[index], index),
      };
    } catch (error) {
      results[index] = { status: "error", error };
    }

    await runNext();
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, () =>
      runNext(),
    ),
  );

  return results;
}

export const attachmentsApi = {
  validateAttachmentFile,

  async getPresignedUploadUrl({ filename, folder, content_type, owner_id }) {
    return requestJson(
      "/attachments/presigned-upload",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, folder, content_type, owner_id }),
      },
      { auth: true, step: "presigned-upload", fileName: filename },
    );
  },

  async uploadFileToStorage(uploadUrl, file, options = {}) {
    return putFileToStorage(uploadUrl, file, options);
  },

  async confirmUpload({
    storage_key,
    original_filename,
    content_type,
    owner_id,
  }) {
    return requestJson(
      "/attachments/confirm-upload",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storage_key,
          original_filename,
          content_type,
          owner_id,
        }),
      },
      { auth: true, step: "confirm-upload", fileName: original_filename },
    );
  },

  /**
   * ownerType сохранён для обратной совместимости с прежними вызовами
   * uploadAttachment(file, ownerType, ownerId), но в JSON не отправляется:
   * фактическая backend-схема ../backend/src/media/schemas.py для
   * PresignedUploadRequest/ConfirmUploadRequest содержит owner_id и не
   * содержит owner_type.
   */
  async uploadAttachment(file, ownerType, ownerId, options = {}) {
    const folder = options.folder || ownerType;
    validateOwnerId(ownerId);
    const { filename, contentType } = validateAttachmentFile(file, options);

    const presignedData = await this.getPresignedUploadUrl({
      filename,
      folder,
      content_type: contentType,
      owner_id: ownerId,
    });

    await this.uploadFileToStorage(presignedData.upload_url, file, {
      signal: options.signal,
    });

    return this.confirmUpload({
      storage_key: presignedData.storage_key,
      original_filename: filename,
      content_type: contentType,
      owner_id: ownerId,
    });
  },

  async uploadAttachments(files, ownerType, ownerId, options = {}) {
    const { concurrency = 3, onFileStateChange } = options;
    const fileList = Array.from(files);
    fileList.forEach((file, index) => {
      onFileStateChange?.(file, { index, status: "pending" });
    });

    return runWithConcurrency(
      fileList,
      async (file, index) => {
        onFileStateChange?.(file, { index, status: "uploading" });
        try {
          const attachment = await this.uploadAttachment(
            file,
            ownerType,
            ownerId,
            options,
          );
          onFileStateChange?.(file, { index, status: "success", attachment });
          return attachment;
        } catch (error) {
          onFileStateChange?.(file, { index, status: "error", error });
          throw error;
        }
      },
      { concurrency },
    );
  },

  async getPresignedDownloadUrl(attachmentId) {
    if (!UUID_RE.test(String(attachmentId || ""))) {
      throw new AttachmentError("Некорректный идентификатор файла.", {
        status: 422,
        code: "INVALID_ATTACHMENT_ID",
        step: "presigned-download",
      });
    }

    return requestJson(
      `/attachments/${encodeURIComponent(attachmentId)}/presigned-download`,
      { method: "GET" },
      { auth: false, step: "presigned-download" },
    );
  },

  async getAttachment(attachmentId) {
    if (!UUID_RE.test(String(attachmentId || ""))) {
      throw new AttachmentError("Некорректный идентификатор файла.", {
        status: 422,
        code: "INVALID_ATTACHMENT_ID",
        step: "get-attachment",
      });
    }

    return requestJson(
      `/attachments/${encodeURIComponent(attachmentId)}`,
      { method: "GET" },
      { auth: false, step: "get-attachment" },
    );
  },

  async fetchAttachmentBlob(attachmentId, options = {}) {
    const { download_url } = await this.getPresignedDownloadUrl(attachmentId);
    return fetchBlobFromStorage(download_url, options);
  },

  async createAttachmentObjectUrl(attachmentId, options = {}) {
    const blob = await this.fetchAttachmentBlob(attachmentId, options);
    const objectUrl = URL.createObjectURL(blob);
    return {
      url: objectUrl,
      revoke: () => URL.revokeObjectURL(objectUrl),
      blob,
    };
  },

  async downloadAttachment(attachmentId, options = {}) {
    const [attachment, blob] = await Promise.all([
      this.getAttachment(attachmentId),
      this.fetchAttachmentBlob(attachmentId, options),
    ]);
    const objectUrl = URL.createObjectURL(blob);

    try {
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = attachment.original_filename || "attachment";
      document.body.appendChild(link);
      link.click();
      link.remove();
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  },
};

export default attachmentsApi;
