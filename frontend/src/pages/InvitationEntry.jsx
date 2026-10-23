import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { acceptInvitation, previewInvitation } from "../utils/api";
import { useSessionStore } from "../stores/sessionStore";
import { usePermissionStore } from "../stores/permissionStore";
import { notify } from "../stores/toastStore";

// The token determines the email and whether registration is available.
// Existing users keep the normal login/accept flow passed as children.
export default function InvitationEntry({ token, children }) {
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setPreview(null);
    setLoadError(null);
    setPassword("");
    setConfirmation("");
    setError("");
    previewInvitation(token).then(
      (result) => { if (active) setPreview(result); },
      (failure) => { if (active) setLoadError(failure); },
    );
    return () => { active = false; };
  }, [token, attempt]);

  if (preview && !preview.registration_required) return children;

  const submit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    if (password !== confirmation) {
      setError("Пароли не совпадают. Проверьте повторный ввод.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const tokens = await acceptInvitation({ token, password });
      const session = useSessionStore.getState();
      session.clearSession();
      session.setTokens(tokens);
      const identity = await session.loadIdentity();
      if (identity) usePermissionStore.getState().setPermissionsFromIdentity(identity);
      session.loadCurrentUser();
      notify("Аккаунт создан. Приглашение принято!");
      navigate("/profile", { replace: true });
    } catch (failure) {
      if (failure.status === 404) setLoadError(failure);
      else if (failure.status === 409) {
        setError("Аккаунт с этим email уже существует. Войдите с вашим паролем.");
      } else {
        setError(failure.validationErrors?.password || (failure.status === 422 || failure.status === 400
          ? "Пароль недостаточно надёжный. Используйте длинный уникальный пароль без имени и email."
          : "Не удалось создать аккаунт. Проверьте соединение и попробуйте ещё раз."));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const invalid = loadError?.status === 404;
  return (
    <section className="container section auth-view">
      <div className="auth-layout">
        <div className="auth-intro">
          <span className="section-top-label">AI Course Lab · Приглашение</span>
          <h1>{loadError ? "Проверьте приглашение" : "Добро пожаловать в команду"}</h1>
          <p>Создайте пароль, чтобы принять приглашение и начать обучение. Вводить email не нужно — он уже указан в приглашении.</p>
        </div>
        <div className="glass-card auth-card" aria-busy={(!preview && !loadError) || submitting}>
          <div className="auth-card-head">
            <span>Регистрация по приглашению</span>
            <strong>{loadError ? "Не удалось продолжить" : "Создайте пароль"}</strong>
          </div>
          {loadError ? (
            <div className="auth-form" role="alert">
              <p>{invalid
                ? "Ссылка недействительна: приглашение использовано, отозвано или срок его действия истёк. Попросите администратора отправить новое приглашение."
                : "Не удалось проверить приглашение. Проверьте соединение и повторите попытку."}</p>
              {!invalid && <button className="btn btn-solid" onClick={() => setAttempt((value) => value + 1)}>Повторить</button>}
              <Link className="btn btn-outline" to="/login">Перейти ко входу</Link>
            </div>
          ) : !preview ? <p role="status">Проверяем приглашение…</p> : (
            <form className="auth-form" onSubmit={submit}>
              <p className="auth-notice">Ваш аккаунт: <strong>{preview.email}</strong><br />Email подтверждён ссылкой из письма.</p>
              <label>
                <span>Новый пароль</span>
                <input name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" required
                  value={password} onChange={(event) => { setPassword(event.target.value); setError(""); }}
                  disabled={submitting} aria-describedby="invite-password-hint invite-password-error" />
              </label>
              <small id="invite-password-hint">Используйте длинный уникальный пароль: например, несколько несвязанных слов с цифрами и символами.</small>
              <label>
                <span>Повторите пароль</span>
                <input name="passwordConfirmation" type={showPassword ? "text" : "password"} autoComplete="new-password" required
                  value={confirmation} onChange={(event) => { setConfirmation(event.target.value); setError(""); }}
                  disabled={submitting} aria-invalid={Boolean(error)} aria-describedby="invite-password-error" />
              </label>
              <button type="button" className="btn btn-ghost" aria-pressed={showPassword}
                onClick={() => setShowPassword((value) => !value)}>{showPassword ? "Скрыть пароли" : "Показать пароли"}</button>
              <p id="invite-password-error" className="auth-field-error" role="alert">{error}</p>
              <button type="submit" className="btn btn-solid auth-submit" disabled={submitting || !password || !confirmation}>
                {submitting ? "Создаём аккаунт…" : "Создать аккаунт и принять приглашение"}
              </button>
              <small>После регистрации вы автоматически войдёте в аккаунт.</small>
              <p className="auth-switch">Уже зарегистрированы? <Link to="/login">Войти в аккаунт</Link></p>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
