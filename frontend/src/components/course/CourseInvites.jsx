/**
 * Карта приглашений курса.
 *
 * Блок внутри карточки курса: форма приглашения по email с ролью
 * (student / teacher / moderator) и список отправленных приглашений.
 *
 * Backend умеет только создавать приглашение (`POST /courses/invitations`)
 * и не отдаёт список приглашений курса, поэтому источник списка — память
 * сессии (`services/invitationApi.js`): после перезагрузки страницы он пустой,
 * пока на сервере не появится GET. Роутов повторной отправки и отмены нет,
 * поэтому действий в списке тоже нет.
 *
 * Рендерится для пользователей с правом управления курсом (course:update).
 */
import { useEffect, useState } from "react";

import { useAppPermissions } from "../../hooks/useAppPermissions";
import {
  INVITATION_ROLE_LABELS,
  INVITATION_ROLES,
  INVITATION_STATUS_LABELS,
} from "../../services/invitationApi";
import { isValidEmail, useInvitationStore } from "../../stores/invitationStore";
import { useSessionStore } from "../../stores/sessionStore";

const EMPTY_INVITATIONS = [];
const DEFAULT_ROLE = INVITATION_ROLES[0];

function formatInvitationDate(value) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export default function CourseInvites({ courseId }) {
  const { canUpdateCourse } = useAppPermissions();
  const currentUserEmail = useSessionStore((state) => state.user?.email || "");

  const invitations = useInvitationStore(
    (state) => state.invitationsByCourse[courseId] || EMPTY_INVITATIONS,
  );
  const isLoading = useInvitationStore((state) =>
    state.loadingCourseIds.has(courseId),
  );
  const error = useInvitationStore(
    (state) => state.errorByCourse[courseId] || "",
  );
  const loadInvitations = useInvitationStore((state) => state.loadInvitations);
  const sendInvitation = useInvitationStore((state) => state.sendInvitation);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState(DEFAULT_ROLE);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!courseId || !canUpdateCourse) return undefined;

    const controller = new AbortController();
    loadInvitations(courseId, { signal: controller.signal }).catch(() => {});
    return () => controller.abort();
  }, [courseId, canUpdateCourse, loadInvitations]);

  if (!courseId || !canUpdateCourse) {
    return null;
  }

  const trimmedEmail = email.trim();
  const canSubmit =
    isValidEmail(trimmedEmail) && Boolean(role) && !isSubmitting;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setFormError("");
    setIsSubmitting(true);

    try {
      await sendInvitation(
        courseId,
        { email: trimmedEmail, role },
        { currentUserEmail },
      );
      setEmail("");
      setRole(DEFAULT_ROLE);
    } catch (submitError) {
      setFormError(
        submitError?.userMessage ||
          submitError?.message ||
          "Не удалось отправить приглашение.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="course-invites" aria-labelledby="course-invites-title">
      <div className="course-invites-head">
        <h3 id="course-invites-title">Приглашения в курс</h3>
        <p className="course-viewer-muted">
          Пригласите студентов и преподавателей по email и назначьте роль.
        </p>
      </div>

      <form className="course-invites-form" onSubmit={handleSubmit} noValidate>
        <label className="course-invites-field">
          <span>Email</span>
          <input
            type="email"
            name="invite-email"
            value={email}
            placeholder="name@example.com"
            autoComplete="email"
            aria-invalid={Boolean(formError)}
            onChange={(event) => {
              setEmail(event.target.value);
              if (formError) setFormError("");
            }}
          />
        </label>

        <label className="course-invites-field">
          <span>Роль</span>
          <select
            name="invite-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            {INVITATION_ROLES.map((roleOption) => (
              <option key={roleOption} value={roleOption}>
                {INVITATION_ROLE_LABELS[roleOption]}
              </option>
            ))}
          </select>
        </label>

        <button
          type="submit"
          className="btn btn-solid course-invites-submit"
          disabled={!canSubmit}
        >
          {isSubmitting ? "Отправляем…" : "Пригласить"}
        </button>
      </form>

      {formError && (
        <p className="course-invites-error" role="alert">
          {formError}
        </p>
      )}
      {!formError && error && (
        <p className="course-invites-error" role="alert">
          {error}
        </p>
      )}

      {isLoading && invitations.length === 0 ? (
        <p className="course-viewer-muted course-invites-state">
          Загрузка приглашений…
        </p>
      ) : error && invitations.length === 0 ? null : invitations.length === 0 ? (
        <div className="course-invites-empty">
          <strong>Пока приглашений нет</strong>
          <p>Отправьте первое через форму ниже.</p>
        </div>
      ) : (
        <ul className="course-invites-list">
          <li className="course-invites-list-head" aria-hidden="true">
            <span>Email</span>
            <span>Роль</span>
            <span>Статус</span>
            <span>Отправлено</span>
          </li>

          {invitations.map((invitation) => (
            <li key={invitation.id} className="course-invite-item">
              <span className="course-invite-email" data-label="Email">
                {invitation.email}
              </span>
              <span className="course-invite-role" data-label="Роль">
                {INVITATION_ROLE_LABELS[invitation.role] || invitation.role}
              </span>
              <span
                className={`course-invite-status is-${invitation.status}`}
                data-label="Статус"
              >
                {INVITATION_STATUS_LABELS[invitation.status] ||
                  invitation.status}
              </span>
              <span className="course-invite-date" data-label="Отправлено">
                {formatInvitationDate(invitation.createdAt)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
