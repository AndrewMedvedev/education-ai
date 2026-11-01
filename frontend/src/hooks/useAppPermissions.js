import { useEffect } from "react";
import {
  AI_MODEL_PERMISSIONS,
  COURSE_PERMISSIONS,
  INVITATION_PERMISSIONS,
  ORGANIZATION_PERMISSIONS,
  usePermissionStore,
} from "../stores/permissionStore";
import { useSessionStore } from "../stores/sessionStore";
import { hasSessionCredentials } from "../utils/api";

export function useAppPermissions() {
  const hasPermission = usePermissionStore((state) => state.hasPermission);
  const hasAnyPermission = usePermissionStore(
    (state) => state.hasAnyPermission,
  );
  usePermissionStore((state) => state.permissions);
  const context = useSessionStore((state) => state.sessionContext);
  const arePermissionsLoaded = usePermissionStore(
    (state) => state.isLoaded && state.context === context,
  );
  const hasHydrated = useSessionStore((state) => state.hasHydrated);
  const loadPermissions = usePermissionStore((state) => state.loadPermissions);
  const accessToken = useSessionStore((state) => state.accessToken);
  const refreshToken = useSessionStore((state) => state.refreshToken);
  const expiresAt = useSessionStore((state) => state.expiresAt);

  const isAuthenticated = hasSessionCredentials({
    accessToken,
    refreshToken,
    expiresAt,
  });
  useEffect(() => {
    if (
      hasHydrated &&
      isAuthenticated &&
      !usePermissionStore.getState().isLoaded
    ) {
      loadPermissions();
    }
  }, [context, hasHydrated, isAuthenticated, loadPermissions]);
  const canCreateCourse =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(COURSE_PERMISSIONS.CREATE);
  // У бэкенда право на прохождение курса называется course:course_read;
  // старого course:read может не быть вовсе, поэтому принимаем любое из двух.
  const canReadCourse =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasAnyPermission([COURSE_PERMISSIONS.READ, COURSE_PERMISSIONS.COURSE_READ]);
  const canOpenCourse =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasAnyPermission([
      COURSE_PERMISSIONS.READ,
      COURSE_PERMISSIONS.COURSE_READ,
      COURSE_PERMISSIONS.UPDATE,
    ]);
  const canBrowseCourses = !isAuthenticated || canReadCourse;
  const canViewCourseInfo = !isAuthenticated || canOpenCourse;
  const canUpdateCourse =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(COURSE_PERMISSIONS.UPDATE);
  const canDeleteCourse =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(COURSE_PERMISSIONS.DELETE);
  const canCreateOrganization =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(ORGANIZATION_PERMISSIONS.CREATE);
  const canReadOrganization =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(ORGANIZATION_PERMISSIONS.READ);
  const canReadOwnOrganization =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(ORGANIZATION_PERMISSIONS.ORGANIZATION_READ);
  const canUpdateOrganization =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(ORGANIZATION_PERMISSIONS.UPDATE);
  const canDeleteOrganization =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(ORGANIZATION_PERMISSIONS.DELETE);
  const canInviteToOrganization =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(INVITATION_PERMISSIONS.ORGANIZATION_INVITE);
  // Раздел «Организации» нужен и тем, у кого есть только права на приглашения.
  const canManageOrganizations =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasAnyPermission([
      ...Object.values(ORGANIZATION_PERMISSIONS),
      ...Object.values(INVITATION_PERMISSIONS),
    ]);
  const canCreateModel =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(AI_MODEL_PERMISSIONS.CREATE);
  const canDeleteModel =
    isAuthenticated &&
    arePermissionsLoaded &&
    hasPermission(AI_MODEL_PERMISSIONS.DELETE);
  const canManageModels = canCreateModel || canDeleteModel;

  return {
    accessToken,
    refreshToken,
    isAuthenticated,
    arePermissionsLoaded:
      hasHydrated && (!isAuthenticated || arePermissionsLoaded),
    canCreateCourse,
    canReadCourse,
    canOpenCourse,
    canBrowseCourses,
    canViewCourseInfo,
    canUpdateCourse,
    canDeleteCourse,
    canCreateOrganization,
    canReadOrganization,
    canReadOwnOrganization,
    canUpdateOrganization,
    canDeleteOrganization,
    canInviteToOrganization,
    canManageOrganizations,
    canCreateModel,
    canDeleteModel,
    canManageModels,
  };
}
