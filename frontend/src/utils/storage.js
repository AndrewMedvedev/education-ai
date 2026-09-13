export function getLocalStorage({ requireWriteAccess = false } = {}) {
  try {
    if (typeof window === "undefined" || !window.localStorage) {
      return null;
    }

    if (requireWriteAccess) {
      const testKey = "__local_storage_access_test__";
      window.localStorage.setItem(testKey, "1");
      window.localStorage.removeItem(testKey);
    }

    return window.localStorage;
  } catch {
    return null;
  }
}

export function readJsonFromStorage(key, fallback = null) {
  const storage = getLocalStorage();
  if (!storage) return fallback;

  try {
    const value = storage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}
