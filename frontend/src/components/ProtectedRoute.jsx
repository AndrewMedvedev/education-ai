import { Navigate, Outlet, useLocation } from "react-router-dom";
import { usePermissionStore } from "../stores/permissionStore";
import { useSessionStore } from "../stores/sessionStore";
import { useAppPermissions } from "../hooks/useAppPermissions";

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
  const { isAuthenticated, arePermissionsLoaded } = useAppPermissions();
  const hasHydrated = useSessionStore((state) => state.hasHydrated);
  const identity = useSessionStore((state) => state.identity);
  const identityError = useSessionStore((state) => state.identityError);
  const membershipId = useSessionStore((state) => state.membershipId);
  const organizationId = useSessionStore((state) => state.organizationId);
  const permissionsError = usePermissionStore((state) => state.error);
  const isLoading = usePermissionStore((state) => state.isLoading);
  const loadPermissions = usePermissionStore((state) => state.loadPermissions);
  const hasAnyPermission = usePermissionStore(
    (state) => state.hasAnyPermission,
  );
  const hasAllPermissions = usePermissionStore(
    (state) => state.hasAllPermissions,
  );
  const requiredPermissions = permissions || (permission ? [permission] : []);

  if (!hasHydrated) {
    return <p className="course-details-text">Восстанавливаем сессию...</p>;
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(buildRedirect(location))}`}
        replace
      />
    );
  }

  if (!membershipId && !organizationId && identity) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(buildRedirect(location))}`}
        replace
      />
    );
  }

  if (
    (!membershipId && !organizationId && !identity) ||
    (requiredPermissions.length > 0 && !arePermissionsLoaded)
  ) {
    return (
      <section className="container section">
        <article className="glass-card">
          <p className="course-details-text" role="status">
            {permissionsError || identityError || "Проверяем права доступа..."}
          </p>
          {(permissionsError || identityError) && (
            <button
              type="button"
              disabled={isLoading}
              onClick={() => loadPermissions()}
            >
              {isLoading ? "Проверяем..." : "Повторить"}
            </button>
          )}
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
