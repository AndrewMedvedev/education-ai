import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import Icon, { Spinner } from "./icons";
import { useDndCourseStore } from "./store";

export const DndActionsContext = createContext({
  pickFiles: () => {},
  requestDelete: () => {},
  previewLesson: () => {},
});

export const useDndActions = () => useContext(DndActionsContext);

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Модальное окно: держит фокус внутри и возвращает его инициатору после закрытия. */
export function Modal({
  title,
  description,
  onClose,
  closeDisabled = false,
  children,
  footer,
  size = "md",
  className = "",
  initialFocusSelector,
}) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const descriptionId = useId();
  const closeRef = useRef(onClose);
  const closeDisabledRef = useRef(closeDisabled);
  closeRef.current = onClose;
  closeDisabledRef.current = closeDisabled;

  useEffect(() => {
    const returnTo = document.activeElement;
    const dialog = dialogRef.current;
    const first =
      (initialFocusSelector && dialog?.querySelector(initialFocusSelector)) ||
      dialog?.querySelector(FOCUSABLE);
    (first || dialog)?.focus();

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        if (!closeDisabledRef.current) closeRef.current?.();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const items = [...dialog.querySelectorAll(FOCUSABLE)].filter(
        (item) => item.offsetParent !== null,
      );
      if (!items.length) return;
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (event.shiftKey && document.activeElement === firstItem) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && document.activeElement === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    };
    dialog?.addEventListener("keydown", onKeyDown);
    return () => {
      dialog?.removeEventListener("keydown", onKeyDown);
      if (returnTo && document.contains(returnTo)) returnTo.focus?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="dnd-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !closeDisabled) onClose?.();
      }}
    >
      <div
        ref={dialogRef}
        className={`dnd-modal dnd-modal--${size} ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
      >
        <header className="dnd-modal-head">
          <h2 id={titleId}>{title}</h2>
          <button
            type="button"
            className="dnd-icon-btn"
            onClick={onClose}
            disabled={closeDisabled}
            aria-label="Закрыть окно"
            title="Закрыть"
          >
            <Icon name="close" />
          </button>
        </header>
        {description ? (
          <p id={descriptionId} className="dnd-modal-description">
            {description}
          </p>
        ) : null}
        <div className="dnd-modal-body">{children}</div>
        {footer ? <footer className="dnd-modal-foot">{footer}</footer> : null}
      </div>
    </div>
  );
}

export function ConfirmDialog() {
  const confirm = useDndCourseStore((state) => state.confirm);
  const closeConfirm = useDndCourseStore((state) => state.closeConfirm);
  const [busy, setBusy] = useState(false);

  useEffect(() => setBusy(false), [confirm]);

  if (!confirm) return null;

  const run = async () => {
    setBusy(true);
    try {
      const result = await confirm.onConfirm?.();
      if (result !== false) closeConfirm();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={confirm.title}
      onClose={closeConfirm}
      closeDisabled={busy}
      size="sm"
      initialFocusSelector="[data-autofocus]"
      footer={
        <>
          <button
            type="button"
            className="dnd-btn dnd-btn--ghost"
            onClick={closeConfirm}
            disabled={busy}
            data-autofocus
          >
            Отмена
          </button>
          <button
            type="button"
            className="dnd-btn dnd-btn--danger"
            onClick={run}
            disabled={busy}
            aria-busy={busy}
          >
            {busy ? <Spinner size={14} /> : <Icon name="trash" size={16} />}
            {busy ? "Удаляем…" : confirm.confirmLabel || "Удалить"}
          </button>
        </>
      }
    >
      <p className="dnd-confirm-text">{confirm.message}</p>
      {confirm.consequences?.length ? (
        <ul className="dnd-confirm-list">
          {confirm.consequences.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </Modal>
  );
}

/** Кнопка-меню с клавиатурной навигацией. Используется как альтернатива перетаскиванию. */
export function ActionMenu({
  label,
  icon = "more",
  items,
  className = "",
  buttonClassName = "dnd-node-btn",
  showLabel = false,
  disabled = false,
  align = "start",
  iconSize = 16,
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const menuId = useId();
  const resolvedItems = typeof items === "function" ? (open ? items() : []) : items;

  const close = useCallback((focusButton = false) => {
    setOpen(false);
    if (focusButton) buttonRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onPointer = (event) => {
      if (!rootRef.current?.contains(event.target)) close();
    };
    document.addEventListener("pointerdown", onPointer, true);
    window.requestAnimationFrame(() =>
      rootRef.current?.querySelector('[role="menuitem"]:not([disabled])')?.focus(),
    );
    return () => document.removeEventListener("pointerdown", onPointer, true);
  }, [open, close]);

  const onMenuKeyDown = (event) => {
    const options = [
      ...rootRef.current.querySelectorAll('[role="menuitem"]:not([disabled])'),
    ];
    const index = options.indexOf(document.activeElement);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      options[(index + 1) % options.length]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      options[(index - 1 + options.length) % options.length]?.focus();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
    } else if (event.key === "Tab") {
      close();
    }
  };

  return (
    <div className={`dnd-menu nodrag nopan ${className}`} ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className={buttonClassName}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={showLabel ? undefined : label}
        data-tip={showLabel || open ? undefined : label}
        disabled={disabled}
        onClick={(event) => {
          event.stopPropagation();
          setOpen((value) => !value);
        }}
      >
        <Icon name={icon} size={iconSize} />
        {showLabel ? <span>{label}</span> : null}
      </button>
      {open ? (
        <div
          id={menuId}
          className={`dnd-menu-list dnd-menu-list--${align} nowheel`}
          role="menu"
          aria-label={label}
          onKeyDown={onMenuKeyDown}
        >
          {resolvedItems.map((item) =>
            item.type === "separator" ? (
              <div key={item.key} className="dnd-menu-sep" role="separator" />
            ) : item.type === "label" ? (
              <div key={item.key} className="dnd-menu-label">
                {item.label}
              </div>
            ) : (
              <button
                key={item.key}
                type="button"
                role="menuitem"
                className={`dnd-menu-item ${item.danger ? "is-danger" : ""}`}
                disabled={item.disabled}
                title={item.hint || item.label}
                onClick={(event) => {
                  event.stopPropagation();
                  close(true);
                  item.onSelect?.();
                }}
              >
                {item.icon ? <Icon name={item.icon} size={16} /> : null}
                <span>{item.label}</span>
                {item.hint && item.disabled ? <small>{item.hint}</small> : null}
              </button>
            ),
          )}
        </div>
      ) : null}
    </div>
  );
}

export function Toasts() {
  const toasts = useDndCourseStore((state) => state.toasts);
  const dismiss = useDndCourseStore((state) => state.dismissToast);
  return (
    <div className="dnd-toasts" aria-live="polite" aria-relevant="additions">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`dnd-toast dnd-toast--${toast.type}`}
          role={toast.type === "error" ? "alert" : "status"}
        >
          <Icon
            name={
              toast.type === "success"
                ? "check"
                : toast.type === "error" || toast.type === "warning"
                  ? "alert"
                  : "info"
            }
            size={18}
          />
          <p>{toast.text}</p>
          {toast.retry ? (
            <button
              type="button"
              className="dnd-toast-action"
              onClick={() => {
                dismiss(toast.id);
                toast.retry();
              }}
            >
              <Icon name="retry" size={14} />
              Повторить
            </button>
          ) : null}
          <button
            type="button"
            className="dnd-icon-btn dnd-icon-btn--sm"
            onClick={() => dismiss(toast.id)}
            aria-label="Скрыть уведомление"
            title="Скрыть"
          >
            <Icon name="close" size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

export function LiveRegion() {
  const announcement = useDndCourseStore((state) => state.announcement);
  return (
    <div className="dnd-visually-hidden" aria-live="polite" role="status">
      {announcement}
    </div>
  );
}

export function SaveIndicator({ status, error }) {
  if (!status) return null;
  const map = {
    dirty: { text: "Есть несохранённые изменения", icon: "edit" },
    saving: { text: "Сохраняем…", icon: null },
    saved: { text: "Сохранено", icon: "check" },
    error: { text: "Ошибка сохранения", icon: "alert" },
  };
  const item = map[status];
  if (!item) return null;
  return (
    <span
      className={`dnd-save dnd-save--${status}`}
      role="status"
      title={status === "error" && error ? error : item.text}
    >
      {item.icon ? <Icon name={item.icon} size={14} /> : <Spinner size={12} />}
      {item.text}
    </span>
  );
}

export function StatusPill({ tone, icon, children, busy = false }) {
  return (
    <span className={`dnd-pill dnd-pill--${tone}`}>
      {busy ? <Spinner size={11} /> : icon ? <Icon name={icon} size={13} /> : null}
      {children}
    </span>
  );
}
