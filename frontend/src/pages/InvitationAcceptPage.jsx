// Принятие приглашения по ссылке из письма: /invitations/:type/accept/:token,
// где type — course или organization. Без входа сохраняем адрес возврата и ведём
// на логин; после входа приглашение принимается автоматически.
import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import SectionTop from "../components/SectionTop";
import { COURSE_ROLE_LABEL } from "../components/course/CourseInviteDialog";
import "../components/course/course-invite.css";
import { usePermissionStore } from "../stores/permissionStore";
import { useSessionStore } from "../stores/sessionStore";
import { useStudentStore } from "../stores/studentStore";
import { notify } from "../stores/toastStore";
import {
  acceptCourseInvitation,
  acceptOrganizationInvitation,
  isTokenExpired,
} from "../utils/api";
import { describeAcceptError, INVITATION_TYPES } from "../utils/invitations";

const ACCEPT = {
  course: acceptCourseInvitation,
  organization: acceptOrganizationInvitation,
};

function loginPathFor(pathname, params = {}) {
  const query = new URLSearchParams({ redirect: pathname, ...params });
  return `/login?${query.toString()}`;
}

function StatusIcon({ tone }) {
  return (
    <span className={`invite-accept-icon is-${tone}`} aria-hidden="true">
      {tone === "success" ? "✓" : tone === "error" ? "!" : ""}
    </span>
  );
}

export default function InvitationAcceptPage() {
  const { type = "", token = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const accessToken = useSessionStore((state) => state.accessToken);
  const refreshToken = useSessionStore((state) => state.refreshToken);
  const expiresAt = useSessionStore((state) => state.expiresAt);
  const userEmail = useSessionStore(
    (state) => state.user?.email || state.identity?.email || "",
  );
  const loadIdentity = useSessionStore((state) => state.loadIdentity);
  const loadCurrentUser = useSessionStore((state) => state.loadCurrentUser);
  const logout = useSessionStore((state) => state.logout);
  const setPermissionsFromIdentity = usePermissionStore(
    (state) => state.setPermissionsFromIdentity,
  );
  const loadMyCourses = useStudentStore((state) => state.loadMyCourses);
  const isAuthenticated = Boolean(
    accessToken && expiresAt && (!isTokenExpired(expiresAt) || refreshToken),
  );
  const config = INVITATION_TYPES[type];
  const [state, setState] = useState({ status: "idle", result: null, error: null });
  const startedFor = useRef("");
  // true, пока сами выходим из аккаунта и уводим на логин с нужными параметрами.
  const [isLeaving, setIsLeaving] = useState(false);

  // После принятия обновляем identity/права/профиль — членство могло изменить доступы.
  const refreshCurrentUser = async () => {
    const identity = await loadIdentity();
    if (identity) setPermissionsFromIdentity(identity);
    loadCurrentUser();
  };

  const accept = async () => {
    setState({ status: "accepting", result: null, error: null });
    try {
      const result = await ACCEPT[type](token);
      await refreshCurrentUser().catch(() => {});

      if (type === "course") {
        loadMyCourses?.().catch(() => {});
        const courseId = result?.course_id || result?.courseId;
        const roleLabel = COURSE_ROLE_LABEL[result?.role] || "участник";
        notify(`Вы присоединились к курсу · ${roleLabel}`);
        if (courseId) {
          navigate(`/course/${courseId}`, { replace: true });
          return;
        }
      } else {
        notify("Вы вступили в организацию");
      }
      setState({ status: "done", result, error: null });
    } catch (error) {
      setState({ status: "error", result: null, error });
    }
  };

  useEffect(() => {
    if (!config || !isAuthenticated || !token) return;
    const key = `${type}:${token}`;
    if (startedFor.current === key) return;
    startedFor.current = key;
    accept();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, isAuthenticated, token, type]);

  if (!config) return <Navigate to="/" replace />;

  const needsLogin =
    !isAuthenticated || (state.status === "error" && state.error?.status === 401);
  if (needsLogin) {
    if (isLeaving) return null;
    // Адрес приглашения уходит в ?redirect=: после входа вернёмся сюда и примем его.
    return <Navigate to={loginPathFor(location.pathname)} replace />;
  }

  const switchAccount = async () => {
    setIsLeaving(true);
    await logout();
    navigate(loginPathFor(location.pathname), { replace: true });
  };

  // Токены выданы под конкретное членство, поэтому в новую организацию
  // можно попасть только через повторный вход — она будет выбрана заранее.
  const goToOrganization = async () => {
    const organizationId =
      state.result?.organization_id || state.result?.organizationId || "";
    setIsLeaving(true);
    await logout();
    navigate(
      loginPathFor("/organizations", organizationId ? { organization: organizationId } : {}),
      { replace: true },
    );
  };

  const errorInfo =
    state.status === "error" ? describeAcceptError(state.error, type) : null;
  const backLink =
    type === "course"
      ? { to: "/courses", label: "Каталог курсов" }
      : { to: "/profile", label: "В личный кабинет" };

  return (
    <section className="container section course-details-view course-invite-accept">
      <SectionTop label="Приглашение" title={config.title} />
      <article className="glass-card course-invite-accept-card" aria-live="polite">
        {state.status === "done" ? (
          <>
            <StatusIcon tone="success" />
            {type === "organization" ? (
              <>
                <h2>Вы вступили в организацию</h2>
                <p>
                  Чтобы перейти в неё, войдите ещё раз — новая организация будет
                  выбрана автоматически. Текущая сессия останется в прежней организации.
                </p>
                <div className="course-invite-accept-actions">
                  <button type="button" className="btn btn-solid" onClick={goToOrganization}>
                    Перейти в организацию
                  </button>
                  <Link className="btn btn-outline" to="/profile">
                    Остаться в текущей
                  </Link>
                </div>
              </>
            ) : (
              <>
                <h2>Вы присоединились к курсу</h2>
                <p>Курс уже появился в вашем списке.</p>
                <div className="course-invite-accept-actions">
                  <Link className="btn btn-solid" to="/profile">
                    В личный кабинет
                  </Link>
                </div>
              </>
            )}
          </>
        ) : errorInfo ? (
          <>
            <StatusIcon tone="error" />
            <h2>{errorInfo.title}</h2>
            <p>{errorInfo.text}</p>
            {userEmail && errorInfo.kind === "wrong-account" ? (
              <p className="invite-accept-identity">
                Сейчас вы вошли как <strong>{userEmail}</strong>
              </p>
            ) : null}
            <div className="course-invite-accept-actions">
              {errorInfo.kind === "retry" ? (
                <button type="button" className="btn btn-solid" onClick={accept}>
                  Повторить
                </button>
              ) : null}
              {errorInfo.kind === "wrong-account" ? (
                <button type="button" className="btn btn-solid" onClick={switchAccount}>
                  Войти под другим аккаунтом
                </button>
              ) : null}
              {errorInfo.kind === "member" ? (
                <Link
                  className="btn btn-solid"
                  to={type === "course" ? "/profile" : "/organizations"}
                >
                  {type === "course" ? "Мои курсы" : "К организации"}
                </Link>
              ) : null}
              <Link className="btn btn-outline" to={backLink.to}>
                {backLink.label}
              </Link>
            </div>
          </>
        ) : (
          <>
            <StatusIcon tone="pending" />
            <h2>Принимаем приглашение…</h2>
            <p>Это займёт пару секунд.</p>
          </>
        )}
      </article>
    </section>
  );
}

// Ссылки из писем бэкенда (/courses/invitations/accept/:token и т.п.) ведут
// на общий маршрут с типом приглашения.
export function InvitationLinkRedirect({ type }) {
  const { token = "" } = useParams();
  return (
    <Navigate
      to={`/invitations/${type}/accept/${encodeURIComponent(token)}`}
      replace
    />
  );
}
