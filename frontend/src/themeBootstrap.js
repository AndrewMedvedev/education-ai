import { readJsonFromStorage } from "./utils/storage";

const getStoredTheme = () =>
  readJsonFromStorage("app-theme-storage", {})?.state?.theme;

const resolveTheme = (theme) => {
  if (theme === "system") {
    return typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  return theme === "dark" || theme === "light" ? theme : "light";
};

document.documentElement.dataset.theme = resolveTheme(getStoredTheme());
