// Окно «Пригласить на курс»: email-ы, роль участника и список текущих участников.
// Пользователь проверяется точечным запросом по email (уникальный индекс) только когда
// email введён целиком — без поиска на каждую букву.
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  fetchCourseInvitationsPage,
  fetchCourseMembersPage,
  fetchUserById,
  inviteToCourse,
  revokeCourseInvitation,
} from "../../utils/api";
import { getErrorMessage } from "../../utils/errors";
import { notify } from "../../stores/toastStore";
import EmailRowsField from "../invite/EmailRowsField";
import { useEmailRows } from "../invite/useEmailRows";
import "./course-invite.css";

export const COURSE_ROLES = [
  {
    id: "student",
    label: "Студент",
    hint: "Проходит курс: теория, практика, ИИ-ментор.",
  },
  {
    id: "moderator",
    label: "Модератор",
    hint: "Помогает вести курс, может приглашать студентов и модераторов.",
  },
  {
    id: "teacher",
    label: "Преподаватель",
    hint: "Редактирует курс и может приглашать участников с любой ролью.",
  },
];

export const COURSE_ROLE_LABEL = Object.fromEntries(
  COURSE_ROLES.map((role) => [role.id, role.label]),
);

const EMPTY_LIST = {
  items: [],
  page: 0,
  total: 0,
  hasNext: false,
  loading: false,
  error: "",
  forbidden: false,
};

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

const MEMBERS_PAGE_SIZE = 20;

const fullNameOf = (user) => user?.full_name || user?.fullName || "";
const memberUserId = (member) => member?.user_id || member?.userId || "";

function inviteErrorMessage(error, roleLabel) {
  if (error?.status === 403) {
    return `Недостаточно прав, чтобы приглашать с ролью «${roleLabel}».`;
  }
  if (error?.status === 404) return "Курс не найден.";
  if (error?.status === 409) return "Этот пользователь уже участник курса.";
  if (error?.status === 422) return "Проверьте email.";
  return getErrorMessage(error, "Не удалось отправить приглашение.");
}

export default function CourseInviteDialog({
  open,
  onClose,
  courseId,
  courseTitle,
  canViewMembers = false,
  currentUserId = "",
}) {
  const titleId = useId();
  const inputId = useId();
  const inputRef = useRef(null);
  const userCache = useRef(new Map());
  const [tab, setTab] = useState("invite");
  const emails = useEmailRows();
  const { draft, rows, reset: resetEmails, sendAll } = emails;
  const [role, setRole] = useState("student");
  const [isSending, setIsSending] = useState(false);
  const [members, setMembers] = useState({
    items: [],
    page: 0,
    total: 0,
    hasNext: false,
    loading: false,
    error: "",
  });
  const [pending, setPending] = useState(EMPTY_LIST);
  const [confirmRevokeId, setConfirmRevokeId] = useState("");
  const [revokingId, setRevokingId] = useState("");
  const [revokeError, setRevokeError] = useState("");
  const [, forceUsersRender] = useState(0);

  const loadMembers = useCallback(
    async (page) => {
      setMembers((current) => ({ ...current, loading: true, error: "" }));
      try {
        const result = await fetchCourseMembersPage(courseId, {
          page,
          size: MEMBERS_PAGE_SIZE,
        });
        setMembers((current) => ({
          items: page === 1 ? result.items : [...current.items, ...result.items],
          page: result.page,
          total: result.total,
          hasNext: result.hasNext,
          loading: false,
          error: "",
        }));
        // Имена подтягиваем только для текущей страницы и кэшируем: не больше
        // MEMBERS_PAGE_SIZE точечных запросов по первичному ключу.
        const missing = [
          ...new Set(result.items.map(memberUserId)),
        ].filter((id) => id && !userCache.current.has(id));
        missing.forEach((id) => userCache.current.set(id, null));
        await Promise.all(
          missing.map((id) =>
            fetchUserById(id)
              .then((user) => userCache.current.set(id, user))
              .catch(() => userCache.current.set(id, false)),
          ),
        );
        if (missing.length) forceUsersRender((value) => value + 1);
      } catch (error) {
        setMembers((current) => ({
          ...current,
          loading: false,
          error: getErrorMessage(error, "Не удалось загрузить участников."),
        }));
      }
    },
    [courseId],
  );

  const loadPending = useCallback(
    async (page) => {
      setPending((current) => ({ ...current, loading: true, error: "" }));
      try {
        const result = await fetchCourseInvitationsPage(courseId, {
          page,
          size: MEMBERS_PAGE_SIZE,
        });
        setPending((current) => ({
          items: page === 1 ? result.items : [...current.items, ...result.items],
          page: result.page,
          total: result.total,
          hasNext: result.hasNext,
          loading: false,
          error: "",
          forbidden: false,
        }));
      } catch (error) {
        setPending({
          ...EMPTY_LIST,
          page: page || 1,
          // 403 — у пользователя нет прав видеть приглашения: просто не показываем блок
          forbidden: error?.status === 403,
          error:
            error?.status === 403
              ? ""
              : getErrorMessage(error, "Не удалось загрузить приглашения."),
        });
      }
    },
    [courseId],
  );

  // Отзыв в два клика: первый — «Отозвать?», второй — запрос.
  const revoke = async (invitationId, onRevoked) => {
    if (!invitationId || revokingId) return;
    if (confirmRevokeId !== invitationId) {
      setConfirmRevokeId(invitationId);
      setRevokeError("");
      return;
    }
    setRevokingId(invitationId);
    try {
      await revokeCourseInvitation(invitationId);
      onRevoked?.();
      setPending((current) => ({
        ...current,
        items: current.items.filter((item) => item.id !== invitationId),
        total: Math.max(0, current.total - 1),
      }));
    } catch (error) {
      setRevokeError(
        error?.status === 409
          ? "Приглашение уже принято — отозвать его нельзя."
          : error?.status === 403
            ? "Недостаточно прав, чтобы отозвать это приглашение."
            : getErrorMessage(error, "Не удалось отозвать приглашение."),
      );
    } finally {
      setRevokingId("");
      setConfirmRevokeId("");
    }
  };

  useEffect(() => {
    if (!confirmRevokeId) return undefined;
    const timer = window.setTimeout(() => setConfirmRevokeId(""), 4000);
    return () => window.clearTimeout(timer);
  }, [confirmRevokeId]);

  useEffect(() => {
    if (!open) return undefined;
    setTab("invite");
    setPending(EMPTY_LIST);
    setConfirmRevokeId("");
    setRevokeError("");
    resetEmails();
    setRole("student");
    setMembers({
      items: [],
      page: 0,
      total: 0,
      hasNext: false,
      loading: false,
      error: "",
    });
    const previouslyFocused = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const timer = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => {
      window.clearTimeout(timer);
      document.body.style.overflow = previousOverflow;
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, [open, courseId]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape" && !isSending) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isSending, onClose, open]);

  useEffect(() => {
    if (open && tab === "members" && canViewMembers && members.page === 0) {
      loadMembers(1);
    }
  }, [canViewMembers, loadMembers, members.page, open, tab]);

  useEffect(() => {
    if (open && tab === "members" && canViewMembers && pending.page === 0) {
      loadPending(1);
    }
  }, [canViewMembers, loadPending, open, pending.page, tab]);

  const roleLabel = COURSE_ROLE_LABEL[role];

  const send = async () => {
    if (isSending) return;
    setIsSending(true);
    const result = await sendAll(
      (email) => inviteToCourse({ courseId, email, role }),
      (error) => inviteErrorMessage(error, roleLabel),
    );
    setIsSending(false);
    if (!result) {
      inputRef.current?.focus();
      return;
    }
    if (members.page > 0) setMembers((current) => ({ ...current, page: 0 }));
    setPending((current) => (current.page > 0 ? { ...current, page: 0 } : current));
    const { sent, total } = result;
    if (!sent.length) return;

    notify(
      sent.length === 1
        ? `Приглашение отправлено на ${sent[0]} · ${roleLabel}`
        : `Отправлено приглашений: ${sent.length} · ${roleLabel}`,
    );
    // Всё ушло — закрываем окно, форма очистится при следующем открытии.
    // Если часть адресов с ошибкой — в списке остаются только они.
    if (sent.length === total) onClose();
  };

  const memberRows = members.items.map((member) => {
        const userId = memberUserId(member);
        const user = userCache.current.get(userId);
        return {
          ...member,
          title:
            user === null || user === undefined
              ? "Загружаем…"
              : user === false
                ? "Пользователь"
                : fullNameOf(user) || user.username || user.email,
          subtitle: user ? user.email : "",
          isMe: Boolean(currentUserId && userId === currentUserId),
        };
      });

  if (!open) return null;

  const host = document.querySelector(".page") || document.body;

  return createPortal(
    <div
      className="course-invite-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSending) onClose();
      }}
    >
      <section
        className="course-invite-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="course-invite-head">
          <div>
            <span className="course-invite-eyebrow">Участники курса</span>
            <h2 id={titleId}>Пригласить на курс</h2>
            {courseTitle ? <p>{courseTitle}</p> : null}
          </div>
          <button
            type="button"
            className="course-invite-close"
            onClick={onClose}
            disabled={isSending}
            aria-label="Закрыть"
            title="Закрыть"
          >
            ×
          </button>
        </header>

        {canViewMembers ? (
          <div className="course-invite-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={tab === "invite"}
              className={tab === "invite" ? "is-active" : ""}
              onClick={() => setTab("invite")}
            >
              Пригласить
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "members"}
              className={tab === "members" ? "is-active" : ""}
              onClick={() => setTab("members")}
            >
              Участники{members.total ? ` · ${members.total}` : ""}
            </button>
          </div>
        ) : null}

        {tab === "invite" ? (
          <div className="course-invite-body">
            <EmailRowsField
              id={inputId}
              inputRef={inputRef}
              emails={emails}
              disabled={isSending}
            />

            <fieldset className="course-invite-roles" disabled={isSending}>
              <legend>Роль в курсе</legend>
              {COURSE_ROLES.map((item) => (
                <label
                  key={item.id}
                  className={`course-invite-role ${role === item.id ? "is-active" : ""}`}
                >
                  <input
                    type="radio"
                    name={`${titleId}-role`}
                    value={item.id}
                    checked={role === item.id}
                    onChange={() => setRole(item.id)}
                  />
                  <strong>{item.label}</strong>
                  <small>{item.hint}</small>
                </label>
              ))}
            </fieldset>
          </div>
        ) : (
          <div className="course-invite-body">
            {revokeError ? (
              <p className="course-invite-error" role="alert">
                {revokeError}
              </p>
            ) : null}
            {!pending.forbidden && (pending.items.length || pending.loading || pending.error) ? (
              <section className="course-invite-section" aria-label="Ожидают ответа">
                <h3 className="course-invite-subtitle">
                  Ожидают ответа{pending.total ? ` · ${pending.total}` : ""}
                </h3>
                {pending.error ? (
                  <p className="course-invite-error" role="alert">
                    {pending.error}
                  </p>
                ) : null}
                {pending.items.length ? (
                  <ul className="course-invite-list">
                    {pending.items.map((item) => (
                      <li key={item.id} className="course-invite-row is-pending">
                        <span className="course-invite-avatar" aria-hidden="true">
                          {String(item.email || "?").slice(0, 1).toUpperCase()}
                        </span>
                        <span className="course-invite-who">
                          <strong>{item.email}</strong>
                          <small>
                            {COURSE_ROLE_LABEL[item.role] || item.role}
                            {item.created_at ? ` · отправлено ${formatDate(item.created_at)}` : ""}
                            {item.expires_at ? ` · действует до ${formatDate(item.expires_at)}` : ""}
                          </small>
                        </span>
                        <button
                          type="button"
                          className={`course-invite-revoke ${confirmRevokeId === item.id ? "is-confirm" : ""}`}
                          onClick={() => revoke(item.id)}
                          disabled={Boolean(revokingId)}
                        >
                          {revokingId === item.id
                            ? "Отзываем…"
                            : confirmRevokeId === item.id
                              ? "Точно отозвать?"
                              : "Отозвать"}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {pending.loading ? (
                  <p className="course-invite-hint" role="status">
                    Загружаем приглашения…
                  </p>
                ) : null}
                {pending.hasNext && !pending.loading ? (
                  <button
                    type="button"
                    className="btn btn-outline course-invite-more"
                    onClick={() => loadPending(pending.page + 1)}
                  >
                    Показать ещё
                  </button>
                ) : null}
              </section>
            ) : null}
            <h3 className="course-invite-subtitle">
              Участники{members.total ? ` · ${members.total}` : ""}
            </h3>
            {members.error ? (
              <p className="course-invite-error" role="alert">
                {members.error}
              </p>
            ) : null}
            {memberRows.length ? (
              <ul className="course-invite-list">
                {memberRows.map((member) => (
                  <li key={member.id || memberUserId(member)} className="course-invite-row">
                    <span className="course-invite-avatar" aria-hidden="true">
                      {String(member.title).slice(0, 1).toUpperCase()}
                    </span>
                    <span className="course-invite-who">
                      <strong>
                        {member.title}
                        {member.isMe ? " (вы)" : ""}
                      </strong>
                      {member.subtitle ? <small>{member.subtitle}</small> : null}
                    </span>
                    <span className={`course-invite-badge is-${member.role}`}>
                      {COURSE_ROLE_LABEL[member.role] || member.role}
                    </span>
                  </li>
                ))}
              </ul>
            ) : !members.loading && !members.error ? (
              <p className="course-invite-hint">
                В курсе пока нет участников. Пригласите первых на вкладке «Пригласить».
              </p>
            ) : null}
            {members.loading ? (
              <p className="course-invite-hint" role="status">
                Загружаем участников…
              </p>
            ) : null}
            {members.hasNext && !members.loading ? (
              <button
                type="button"
                className="btn btn-outline course-invite-more"
                onClick={() => loadMembers(members.page + 1)}
              >
                Показать ещё
              </button>
            ) : null}
          </div>
        )}

        {tab === "invite" ? (
          <footer className="course-invite-foot">
            <span className="course-invite-summary" aria-live="polite">
              {rows.length > 1 ? `Адресов: ${rows.length}` : ""}
            </span>
            <button
              type="button"
              className="btn btn-outline"
              onClick={onClose}
              disabled={isSending}
            >
              Отмена
            </button>
            <button
              type="button"
              className="btn btn-solid"
              // Не уводим фокус из поля: иначе blur добавит строку, окно вырастет
              // и кнопка «уедет» из-под курсора до того, как сработает click.
              onMouseDown={(event) => event.preventDefault()}
              onClick={send}
              disabled={isSending || (!rows.length && !draft.trim())}
            >
              {isSending
                ? "Отправляем…"
                : rows.length > 1
                  ? `Пригласить (${rows.length})`
                  : "Пригласить"}
            </button>
          </footer>
        ) : null}
      </section>
    </div>,
    host,
  );
}
