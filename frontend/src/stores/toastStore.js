import { create } from "zustand";

// Короткие всплывающие уведомления («Приглашение отправлено» и т.п.).
let nextToastId = 0;

export const useToastStore = create((set, get) => ({
  toasts: [],

  show: (message, { tone = "success", duration = 4500 } = {}) => {
    if (!message) return null;
    nextToastId += 1;
    const id = nextToastId;
    set({ toasts: [...get().toasts, { id, message, tone }].slice(-3) });
    if (duration > 0) {
      window.setTimeout(() => get().dismiss(id), duration);
    }
    return id;
  },

  dismiss: (id) =>
    set({ toasts: get().toasts.filter((toast) => toast.id !== id) }),
}));

export const notify = (message, options) =>
  useToastStore.getState().show(message, options);
