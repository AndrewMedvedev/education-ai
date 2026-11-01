export const RESELECT_CREATOR_FILES = "После перезагрузки сохранены только сведения о файлах. Выберите файлы повторно или удалите их перед отправкой.";

// Explicit whitelist: never pass File (or its contents) into JSON persistence.
export function creatorFileMetadata(files = []) {
  return files.map(({ id, name, sizeKb, size, lastModified }) => ({
    id, name, sizeKb, size, lastModified,
  }));
}

export const needsFileReselection = (files) => files.some((item) => !item.file);
