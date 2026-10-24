import { useEffect, useState } from "react";
import { fetchOrganizationInvitations, resendOrganizationInvitation, revokeOrganizationInvitation } from "../../utils/api";
import { usePermissionStore } from "../../stores/permissionStore";
import { notify } from "../../stores/toastStore";

const STATUS = { pending: "Ожидает принятия", accepted: "Принято", expired: "Срок истёк", revoked: "Отозвано" };
const date = (value) => value ? new Date(value).toLocaleString("ru-RU") : "—";

export default function OrganizationInvitations({ revision }) {
  const canRevoke = usePermissionStore((state) => state.hasPermission("organization-invitations:delete"));
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pending, setPending] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [confirmation, setConfirmation] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setConfirmation("");
    fetchOrganizationInvitations(page).then((result) => {
      if (active) setData(result);
    }).catch(() => {
      if (active) setError("Не удалось загрузить приглашения. Повторите попытку.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, revision, refresh]);

  const act = async (invitation, action) => {
    if (pending) return;
    setPending(`${invitation.source}:${invitation.id}`);
    setError("");
    try {
      await (action === "revoke" ? revokeOrganizationInvitation : resendOrganizationInvitation)(invitation.id, invitation.source);
      notify(action === "revoke" ? "Приглашение отозвано" : "Приглашение отправлено повторно");
      setConfirmation("");
      setRefresh((value) => value + 1);
    } catch (failure) {
      setError(failure.status === 403 ? "Недостаточно прав для этого действия."
        : failure.status === 409 ? "Статус приглашения изменился или пользователь уже состоит в организации. Обновите список."
        : "Не удалось выполнить действие. Обновите список и попробуйте ещё раз.");
    } finally { setPending(""); }
  };

  return (
    <article className="glass-card organization-panel" aria-busy={loading}>
      <div className="organization-panel-head">
        <h3>Отправленные приглашения</h3>
        <button type="button" className="btn btn-outline" disabled={loading || Boolean(pending)} onClick={() => setRefresh((value) => value + 1)}>Обновить</button>
      </div>
      {error && <p role="alert" className="auth-field-error">{error}</p>}
      {loading ? <p role="status">Загружаем приглашения…</p> : data && (
        <>
          {!data.items.length && <p className="organization-muted">Приглашения ещё не отправлены.</p>}
          <div className="organization-list">
            {data.items.map((invitation) => {
              const key = `${invitation.source}:${invitation.id}`;
              const actionable = ["pending", "expired"].includes(invitation.status);
              return (
                <article className="organization-card" key={key}>
                  <div className="organization-panel-head">
                    <strong className="organization-invitation-email">{invitation.email}</strong>
                    <span role="status">{STATUS[invitation.status] || invitation.status}</span>
                  </div>
                  <p className="organization-muted">Создано: {date(invitation.created_at)} · Действует до: {date(invitation.expires_at)}</p>
                  {invitation.used_at && <p>Принято: {date(invitation.used_at)}</p>}
                  {invitation.revoked_at && <p>Отозвано: {date(invitation.revoked_at)}</p>}
                  {actionable && <div className="organization-panel-actions">
                    <button type="button" className="btn btn-outline" disabled={Boolean(pending)} onClick={() => act(invitation, "resend")}>Повторить отправку</button>
                    {canRevoke && (confirmation === key ? <>
                      <span>Отозвать приглашение?</span>
                      <button type="button" className="btn btn-outline organization-danger-btn" disabled={Boolean(pending)} onClick={() => act(invitation, "revoke")}>Да, отозвать</button>
                      <button type="button" className="btn btn-ghost" disabled={Boolean(pending)} onClick={() => setConfirmation("")}>Отмена</button>
                    </> : <button type="button" className="btn btn-outline organization-danger-btn" disabled={Boolean(pending)} onClick={() => setConfirmation(key)}>Отозвать</button>)}
                    {pending === key && <span role="status">Выполняем…</span>}
                  </div>}
                </article>
              );
            })}
          </div>
          {data.pages > 1 && <nav className="organization-panel-actions" aria-label="Страницы приглашений">
            <button type="button" className="btn btn-outline" disabled={page <= 1 || Boolean(pending)} onClick={() => setPage((value) => value - 1)}>Назад</button>
            <span>{page} / {data.pages}</span>
            <button type="button" className="btn btn-outline" disabled={page >= data.pages || Boolean(pending)} onClick={() => setPage((value) => value + 1)}>Вперёд</button>
          </nav>}
        </>
      )}
    </article>
  );
}
