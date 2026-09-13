import { create } from "zustand";
import { persist } from "zustand/middleware";

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
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    },
  ),
);
