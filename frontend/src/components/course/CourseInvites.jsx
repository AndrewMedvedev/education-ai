/**
 * Карта приглашений курса.
 *
 * Блок внутри карточки курса: форма приглашения по email с ролью
 * (student / teacher / moderator) и список уже отправленных приглашений
 * со статусами и действиями «повторно отправить» / «отменить».
 *
 * Рендерится для пользователей с правом управления курсом (course:update),
 * а в демо-режиме (IS_INVITATION_MOCK) — на любом курсе, с пометкой о моках.
 */
import { useEffect, useState } from "react";

import { useAppPermissions } from "../../hooks/useAppPermissions";
import {
  INVITATION_ROLE_LABELS,
  INVITATION_ROLES,
  INVITATION_STATUS_LABELS,
  IS_INVITATION_MOCK,
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
  const pendingIds = useInvitationStore((state) => state.pendingInvitationIds);
  const loadInvitations = useInvitationStore((state) => state.loadInvitations);
  const sendInvitation = useInvitationStore((state) => state.sendInvitation);
  const resendInvitation = useInvitationStore(
    (state) => state.resendInvitation,
  );
  const cancelInvitation = useInvitationStore(
    (state) => state.cancelInvitation,
  );

  const [email, setEmail] = useState("");
  const [role, setRole] = useState(DEFAULT_ROLE);
  const [formError, setFormError] = useState("");
  const [actionError, setActionError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // В демо-режиме блок показываем и без права управления курсом.
    if (!courseId || (!canUpdateCourse && !IS_INVITATION_MOCK)) return undefined;

    const controller = new AbortController();
    loadInvitations(courseId, { signal: controller.signal }).catch(() => {});
    return () => controller.abort();
  }, [courseId, canUpdateCourse, loadInvitations]);

  if (!courseId || (!canUpdateCourse && !IS_INVITATION_MOCK)) {
    return null;
  }

  const trimmedEmail = email.trim();
  const isInvitationEndpointUnavailable = error.includes(
    "пока не подключён на сервере",
  );
  const isCreateDisabled = IS_INVITATION_MOCK;
  const canSubmit =
    isValidEmail(trimmedEmail) &&
    Boolean(role) &&
    !isSubmitting &&
    !isCreateDisabled &&
    !isInvitationEndpointUnavailable;

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

  async function handleResend(invitationId) {
    setActionError("");

    try {
      await resendInvitation(courseId, invitationId);
    } catch (resendError) {
      setActionError(
        resendError?.userMessage ||
          resendError?.message ||
          "Не удалось отправить приглашение повторно.",
      );
    }
  }

  async function handleCancel(invitationId) {
    setActionError("");

    try {
      await cancelInvitation(courseId, invitationId);
    } catch (cancelError) {
      setActionError(
        cancelError?.userMessage ||
          cancelError?.message ||
          "Не удалось отменить приглашение.",
      );
    }
  }

  return (
    <section className="course-invites" aria-labelledby="course-invites-title">
      <div className="course-invites-head">
        <h3 id="course-invites-title">Приглашения в курс</h3>
        <p className="course-viewer-muted">
          Пригласите студентов и преподавателей по email и назначьте роль.
        </p>
        {IS_INVITATION_MOCK && (
          <p className="course-invites-demo" role="status">
            Демо-режим: данные замоканы, создание приглашений недоступно.
          </p>
        )}
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
          title={
            isCreateDisabled ? "Создание недоступно в демо-режиме" : undefined
          }
        >
          {isSubmitting ? "Отправляем…" : "Пригласить"}
        </button>
      </form>

      {formError && (
        <p className="course-invites-error" role="alert">
          {formError}
        </p>
      )}
      {actionError && (
        <p className="course-invites-error" role="alert">
          {actionError}
        </p>
      )}
      {error && (
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
          <strong>Пока нет приглашений</strong>
          <p>Отправьте первое приглашение — оно появится здесь со статусом «Ожидает».</p>
        </div>
      ) : (
        <ul className="course-invites-list">
          <li className="course-invites-list-head" aria-hidden="true">
            <span>Email</span>
            <span>Роль</span>
            <span>Статус</span>
            <span>Отправлено</span>
            <span>Действия</span>
          </li>

          {invitations.map((invitation) => {
            const isInvitationPending = pendingIds.has(invitation.id);

            return (
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
                <span className="course-invite-actions" data-label="Действия">
                  <button
                    type="button"
                    className="btn btn-outline course-invite-action"
                    disabled={isInvitationPending}
                    onClick={() => handleResend(invitation.id)}
                  >
                    Повторно
                  </button>
                  <button
                    type="button"
                    className="btn btn-flat course-invite-action is-danger"
                    disabled={isInvitationPending}
                    onClick={() => handleCancel(invitation.id)}
                  >
                    Отменить
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
