import { usePermissionStore } from "../stores/permissionStore";

export default function PermissionGate({
  permission,
  permissions,
  requireAll = true,
  fallback = null,
  children,
}) {
  const hasAnyPermission = usePermissionStore(
    (state) => state.hasAnyPermission,
  );
  const hasAllPermissions = usePermissionStore(
    (state) => state.hasAllPermissions,
  );
  const requiredPermissions = permissions || (permission ? [permission] : []);
  const isAllowed =
    requiredPermissions.length === 0 ||
    (requireAll
      ? hasAllPermissions(requiredPermissions)
      : hasAnyPermission(requiredPermissions));

  return isAllowed ? children : fallback;
}
