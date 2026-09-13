import { Navigate, Outlet, useLocation } from "react-router-dom";
import { usePermissionStore } from "../stores/permissionStore";
import { useSessionStore } from "../stores/sessionStore";
import { isTokenExpired } from "../utils/api";

function buildRedirect(location) {
  return `${location.pathname}${location.search}`;
}

function AccessDenied() {
  return (
    <section className="container section">
      <article className="glass-card course-viewer-error">
        <h1>Доступ ограничен</h1>
        <p>
          У вашей роли нет разрешений для этого раздела. Обратитесь к
          администратору организации, чтобы получить доступ.
        </p>
      </article>
    </section>
  );
}

export default function ProtectedRoute({
  children,
  permission,
  permissions,
  requireAll = true,
  fallback = <AccessDenied />,
}) {
  const location = useLocation();
  const accessToken = useSessionStore((state) => state.accessToken);
  const refreshToken = useSessionStore((state) => state.refreshToken);
  const expiresAt = useSessionStore((state) => state.expiresAt);
  const membershipId = useSessionStore((state) => state.membershipId);
  const organizationId = useSessionStore((state) => state.organizationId);
  const arePermissionsLoaded = usePermissionStore((state) => state.isLoaded);
  const hasAnyPermission = usePermissionStore(
    (state) => state.hasAnyPermission,
  );
  const hasAllPermissions = usePermissionStore(
    (state) => state.hasAllPermissions,
  );
  const isAuthenticated = Boolean(
    accessToken && expiresAt && (!isTokenExpired(expiresAt) || refreshToken),
  );
  const requiredPermissions = permissions || (permission ? [permission] : []);

  if (!isAuthenticated) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(buildRedirect(location))}`}
        replace
      />
    );
  }

  if (!membershipId && !organizationId) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(buildRedirect(location))}`}
        replace
      />
    );
  }

  if (requiredPermissions.length > 0 && !arePermissionsLoaded) {
    return (
      <section className="container section">
        <article className="glass-card">
          <p className="course-details-text">Проверяем права доступа...</p>
        </article>
      </section>
    );
  }

  const isAllowed =
    requiredPermissions.length === 0 ||
    (requireAll
      ? hasAllPermissions(requiredPermissions)
      : hasAnyPermission(requiredPermissions));

  if (!isAllowed) {
    return fallback;
  }

  return children || <Outlet />;
}
