export const MEDIA_FOLDERS = Object.freeze({
  AVATAR: "avatar",
  COURSE_IMAGES: "course-images",
});

export const MEDIA_BASE_URL = String(
  import.meta.env.VITE_MEDIA_BASE_URL ||
    import.meta.env.VITE_STORAGE_PUBLIC_HOST ||
    "http://localhost:9000/ai-course",
).replace(/\/+$/, "");

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function getMediaId(value) {
  const source = String(value || "").trim();
  if (!source) return "";
  if (UUID_RE.test(source)) return source;

  const withoutQuery = source.split(/[?#]/)[0] || "";
  const filename = withoutQuery.split("/").filter(Boolean).pop() || "";
  return filename;
}

export function getMediaUrl(userId, folder, imageId) {
  const normalizedUserId = String(userId || "").trim();
  const normalizedFolder = String(folder || "")
    .trim()
    .replace(/^\/+|\/+$/g, "");
  const normalizedImageId = getMediaId(imageId);

  if (!normalizedUserId || !normalizedFolder || !normalizedImageId) return "";

  return `${MEDIA_BASE_URL}/${encodeURIComponent(normalizedFolder)}/${encodeURIComponent(normalizedUserId)}/${encodeURIComponent(normalizedImageId)}`;
}
