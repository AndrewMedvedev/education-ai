import { useToastStore } from "../stores/toastStore";
import "./toaster.css";

export default function Toaster() {
  const toasts = useToastStore((state) => state.toasts);
  const dismiss = useToastStore((state) => state.dismiss);

  return (
    <div className="toaster" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast is-${toast.tone}`}
          role={toast.tone === "error" ? "alert" : "status"}
        >
          <span className="toast-icon" aria-hidden="true">
            {toast.tone === "error" ? "!" : "✓"}
          </span>
          <p>{toast.message}</p>
          <button
            type="button"
            className="toast-close"
            onClick={() => dismiss(toast.id)}
            aria-label="Закрыть уведомление"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
