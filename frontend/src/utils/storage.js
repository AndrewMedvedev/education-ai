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

// Always return an adapter, even without storage, so Zustand completes hydration.
export function createSafeJSONStorage(getStorage = getLocalStorage) {
  return {
    getItem: (name) => {
      try {
        return JSON.parse(getStorage()?.getItem(name) || "null");
      } catch {
        return null;
      }
    },
    setItem: (name, value) => {
      try {
        getStorage()?.setItem(name, JSON.stringify(value));
      } catch {
        // Quota/private-mode failures must not escape live store actions.
      }
    },
    removeItem: (name) => {
      try {
        getStorage()?.removeItem(name);
      } catch {
        // Clearing live state must not depend on persistent storage.
      }
    },
  };
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
