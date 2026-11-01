import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createSafeJSONStorage } from "../utils/storage";

const THEME_STORAGE_KEY = "app-theme-storage";
const THEME_STORAGE_VERSION = 1;
const SUPPORTED_THEMES = new Set(["light", "dark", "system"]);

const getSystemTheme = () => {
  if (typeof window === "undefined" || !window.matchMedia) {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

export const resolveTheme = (theme) =>
  theme === "system" ? getSystemTheme() : theme;

export const useThemeStore = create(
  persist(
    (set, get) => ({
      theme: "light",
      hasHydrated: false,

      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      setTheme: (theme) => {
        if (!SUPPORTED_THEMES.has(theme)) return;
        set({ theme });
      },
      toggleTheme: () => {
        const currentTheme = resolveTheme(get().theme);
        set({ theme: currentTheme === "dark" ? "light" : "dark" });
      },
    }),
    {
      name: THEME_STORAGE_KEY,
      version: THEME_STORAGE_VERSION,
      storage: createSafeJSONStorage(),
      partialize: (state) => ({
        theme: SUPPORTED_THEMES.has(state.theme) ? state.theme : "light",
      }),
      migrate: (persistedState, version) => {
        if (version !== THEME_STORAGE_VERSION) {
          return { theme: "light" };
        }

        return SUPPORTED_THEMES.has(persistedState?.theme)
          ? persistedState
          : { theme: "light" };
      },
      // migrate is skipped for matching versions; never merge actions/flags.
      merge: (persistedState, currentState) => ({
        ...currentState,
        theme: SUPPORTED_THEMES.has(persistedState?.theme)
          ? persistedState.theme
          : currentState.theme,
      }),
      onRehydrateStorage: (initialState) => (state) => {
        (state || initialState).setHasHydrated(true);
      },
    },
  ),
);
