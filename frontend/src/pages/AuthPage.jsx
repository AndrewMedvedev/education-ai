import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useSessionStore } from "../stores/sessionStore";
import { isTokenExpired } from "../utils/api";

function getRedirectPath(search) {
  const params = new URLSearchParams(search);
  const redirect = params.get("redirect");
  if (!redirect || !redirect.startsWith("/") || redirect.startsWith("//")) {
    return "/profile";
  }

  const redirectPathname = redirect.split(/[?#]/, 1)[0];
  return ["/login", "/register"].includes(redirectPathname)
    ? "/profile"
    : redirect;
}

function getMembershipId(membership) {
  return membership?.id || membership?.membership_id;
}

function getOrganizationName(membership) {
  return (
    membership?.organization?.name ||
    membership?.organization_name ||
    membership?.organization?.title ||
    "Организация без названия"
  );
}

export default function AuthPage({ mode = "login" }) {
  const isRegister = mode === "register";
  const navigate = useNavigate();
  const location = useLocation();
  const redirectPath = useMemo(
    () => getRedirectPath(location.search),
    [location.search],
  );
  const accessToken = useSessionStore((state) => state.accessToken);
  const refreshToken = useSessionStore((state) => state.refreshToken);
  const expiresAt = useSessionStore((state) => state.expiresAt);
  const membershipId = useSessionStore((state) => state.membershipId);
  const organizationId = useSessionStore((state) => state.organizationId);
  const loginStep = useSessionStore((state) => state.loginStep);
  const memberships = useSessionStore((state) => state.memberships);
  const isLoading = useSessionStore((state) => state.isLoading);
  const error = useSessionStore((state) => state.error);
  const validationErrors = useSessionStore((state) => state.validationErrors);
  const loginWithCredentials = useSessionStore(
    (state) => state.loginWithCredentials,
  );
  const selectMembership = useSessionStore((state) => state.selectMembership);
  const resetOrganizationSelection = useSessionStore(
    (state) => state.resetOrganizationSelection,
  );
  const [selectedMembershipId, setSelectedMembershipId] = useState("");

  useEffect(() => {
    const hasActiveSession = Boolean(
      accessToken &&
      expiresAt &&
      (!isTokenExpired(expiresAt) || refreshToken) &&
      (membershipId || organizationId),
    );
    if (hasActiveSession) {
      navigate(redirectPath, { replace: true });
    }
  }, [
    accessToken,
    expiresAt,
    membershipId,
    navigate,
    organizationId,
    redirectPath,
    refreshToken,
  ]);

  useEffect(() => {
    if (!selectedMembershipId && memberships.length === 1) {
      setSelectedMembershipId(getMembershipId(memberships[0]) || "");
    }
  }, [memberships, selectedMembershipId]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);

    if (isRegister) {
      return;
    }

    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");

    if (!email || !password) {
      return;
    }

    try {
      await loginWithCredentials({ email, password });
    } catch {
      // Ошибка уже нормализована и сохранена в session store без чувствительных данных.
    }
  };

  const handleSelectMembership = async (event) => {
    event.preventDefault();
    if (!selectedMembershipId) return;

    try {
      await selectMembership(selectedMembershipId);
    } catch {
      // Ошибка выбора организации отображается ниже.
    }
  };

  return (
    <section
      className={`container section auth-view ${loginStep === "organization" ? "auth-view-organization" : ""}`}
    >
      <div className="auth-layout">
        <div className="auth-intro">
          <span className="section-top-label">AI Course Lab</span>
          <h1
            className={
              isRegister || loginStep === "organization"
                ? undefined
                : "auth-login-title"
            }
          >
            {isRegister
              ? "Создайте учебный профиль"
              : loginStep === "organization"
                ? "Продолжите в организации"
                : "С возвращением"}
          </h1>
          <p>
            {loginStep === "organization"
              ? "Выбор организации определяет рабочее пространство, роли и доступные курсы. Для смены организации нужно войти заново."
              : "Сохраняйте прогресс, проходите курсы и возвращайтесь к материалам с любого устройства."}
          </p>
        </div>

        <div className="glass-card auth-card">
          <div className="auth-card-head">
            <span>{isRegister ? "Новый профиль" : "Вход в платформу"}</span>
            <strong>
              {isRegister
                ? "Регистрация"
                : loginStep === "organization"
                  ? "Организация"
                  : "Авторизация"}
            </strong>
          </div>

          {isRegister ? (
            <div className="auth-form">
              <p className="auth-notice">Регистрация пока не подключена.</p>
              <Link className="btn btn-solid auth-submit" to="/login">
                Войти
              </Link>
            </div>
          ) : loginStep === "organization" ? (
            <form className="auth-form" onSubmit={handleSelectMembership}>
              <div className="auth-organization-list">
                {memberships.length ? (
                  memberships.map((membership) => {
                    const membershipId = getMembershipId(membership);
                    return (
                      <label
                        className="auth-organization-option"
                        key={membershipId}
                      >
                        <input
                          type="radio"
                          name="membership"
                          value={membershipId}
                          checked={selectedMembershipId === membershipId}
                          onChange={() => setSelectedMembershipId(membershipId)}
                        />
                        <span>
                          <strong>{getOrganizationName(membership)}</strong>
                          {membership?.joined_at && (
                            <small>
                              Участник с{" "}
                              {new Date(
                                membership.joined_at,
                              ).toLocaleDateString("ru-RU")}
                            </small>
                          )}
                        </span>
                      </label>
                    );
                  })
                ) : (
                  <p className="auth-notice">
                    Для этого пользователя не найдено доступных организаций.
                  </p>
                )}
              </div>
              <button
                type="submit"
                className="btn btn-solid auth-submit"
                disabled={isLoading || !selectedMembershipId}
              >
                {isLoading ? "Получаем токены..." : "Продолжить"}
              </button>
              <button
                type="button"
                className="btn btn-ghost auth-submit"
                onClick={resetOrganizationSelection}
                disabled={isLoading}
              >
                Войти заново
              </button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              <label>
                <span>Email</span>
                <input
                  type="email"
                  name="email"
                  placeholder="you@example.com"
                  required
                  aria-invalid={Boolean(validationErrors.email)}
                />
                {validationErrors.email && (
                  <small className="auth-field-error">
                    {validationErrors.email}
                  </small>
                )}
              </label>
              <label>
                <span>Пароль</span>
                <input
                  type="password"
                  name="password"
                  placeholder="Введите пароль"
                  required
                  aria-invalid={Boolean(validationErrors.password)}
                />
                {validationErrors.password && (
                  <small className="auth-field-error">
                    {validationErrors.password}
                  </small>
                )}
              </label>
              <button
                type="submit"
                className="btn btn-solid auth-submit"
                disabled={isLoading}
              >
                {isLoading ? "Вход..." : "Войти"}
              </button>
            </form>
          )}

          {error && <p className="auth-notice">{error}</p>}

          {!isRegister && loginStep === "credentials" && (
            <p className="auth-switch">
              Еще нет профиля? <Link to="/register">Зарегистрироваться</Link>
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
