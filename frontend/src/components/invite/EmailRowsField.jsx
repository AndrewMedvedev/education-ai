// Поле «Email» с несколькими адресами и список добавленных адресов со статусами.
const fullNameOf = (user) => user?.full_name || user?.fullName || "";

function userTitle(user) {
  if (!user) return "";
  const name = fullNameOf(user);
  const username = user.username ? `@${user.username}` : "";
  return [name, username].filter(Boolean).join(" · ");
}

export default function EmailRowsField({
  id,
  inputRef,
  emails,
  disabled = false,
  newUserHint = "Нет в системе — получит ещё и приглашение на регистрацию",
  foundUserHint = (user) => userTitle(user) || "Есть в системе",
}) {
  const { draft, setDraft, draftError, setDraftError, rows, addEmails, removeRow } = emails;

  const rowText = (row) => {
    if (row.status === "checking") return "Проверяем…";
    if (row.status === "found") return foundUserHint(row.user);
    if (row.status === "new") return newUserHint;
    if (row.status === "unknown") {
      return "Не удалось проверить — приглашение всё равно можно отправить";
    }
    if (row.status === "sending") return "Отправляем…";
    return row.message;
  };

  return (
    <>
      <div className="course-invite-field">
        <label htmlFor={id}>Email</label>
        <div className={`course-invite-input ${draftError ? "has-error" : ""}`}>
          <input
            ref={inputRef}
            id={id}
            type="text"
            inputMode="email"
            autoComplete="off"
            placeholder="name@example.com"
            value={draft}
            disabled={disabled}
            onChange={(event) => {
              setDraft(event.target.value);
              if (draftError) setDraftError("");
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === "," || event.key === ";") {
                event.preventDefault();
                addEmails(draft);
              } else if (event.key === "Backspace" && !draft && rows.length && !disabled) {
                removeRow(rows[rows.length - 1].email);
              }
            }}
            onBlur={() => draft.trim() && addEmails(draft)}
            onPaste={(event) => {
              const text = event.clipboardData.getData("text");
              if (/[\s,;]/.test(text.trim())) {
                event.preventDefault();
                addEmails(`${draft} ${text}`);
              }
            }}
            aria-describedby={`${id}-hint`}
            aria-invalid={Boolean(draftError)}
          />
          <button
            type="button"
            className="course-invite-add"
            onClick={() => addEmails(draft)}
            disabled={!draft.trim() || disabled}
          >
            Добавить
          </button>
        </div>
        <small
          id={`${id}-hint`}
          className={draftError ? "course-invite-error" : "course-invite-hint"}
          role={draftError ? "alert" : undefined}
        >
          {draftError ||
            "Enter или запятая — добавить. Можно вставить сразу несколько адресов."}
        </small>
      </div>

      {rows.length ? (
        <ul className="course-invite-list" aria-live="polite">
          {rows.map((row) => (
            <li key={row.email} className={`course-invite-row is-${row.status}`}>
              <span className="course-invite-avatar" aria-hidden="true">
                {(fullNameOf(row.user) || row.email).slice(0, 1).toUpperCase()}
              </span>
              <span className="course-invite-who">
                <strong>{row.email}</strong>
                <small>{rowText(row)}</small>
              </span>
              <button
                type="button"
                className="course-invite-remove"
                onClick={() => removeRow(row.email)}
                disabled={disabled}
                aria-label={`Убрать ${row.email}`}
                title="Убрать"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}
