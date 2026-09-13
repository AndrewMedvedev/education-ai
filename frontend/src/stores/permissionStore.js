import { create } from "zustand";
import { fetchIdentity } from "../utils/api";

export const COURSE_PERMISSIONS = {
  READ: "course:read",
  COURSE_READ: "course:course_read",
  CREATE: "course:create",
  UPDATE: "course:update",
  DELETE: "course:delete",
};

export const ORGANIZATION_PERMISSIONS = {
  CREATE: "organization:create",
  READ: "organization:read",
  ORGANIZATION_READ: "organization:organization_read",
  UPDATE: "organization:update",
  DELETE: "organization:delete",
};

export const AI_MODEL_PERMISSIONS = {
  CREATE: "ai_model:create",
  DELETE: "ai_model:delete",
};

function normalizePermissionString(value) {
  const permission = String(value || "")
    .trim()
    .toLowerCase();
  if (!permission) return "";

  const withoutScope = permission.split(":")[0];
  const [resource, action] = withoutScope.includes(".")
    ? withoutScope.split(".", 2)
    : permission.split(":", 2);

  if (!resource || !action) return permission.replace(".", ":");

  return `${resource}:${action}`;
}

function normalizePermissionCode(permission) {
  if (typeof permission === "string") {
    return normalizePermissionString(permission);
  }

  if (!permission || typeof permission !== "object") {
    return "";
  }

  const rawCode = permission.code || permission.name || permission.permission;
  if (typeof rawCode === "string" && rawCode.trim()) {
    return normalizePermissionString(rawCode);
  }

  if (permission.resource && permission.action) {
    return normalizePermissionString(
      `${permission.resource}:${permission.action}`,
    );
  }

  return "";
}

function extractPermissionsFromIdentity(identity) {
  if (Array.isArray(identity)) {
    return identity.map(normalizePermissionCode).filter(Boolean);
  }

  if (!identity || typeof identity !== "object") {
    return [];
  }

  const directPermissions =
    identity.permissions ||
    identity.effective_permissions ||
    identity.effectivePermissions ||
    identity.user_permissions ||
    identity.userPermissions ||
    identity.grants ||
    [];

  const membershipPermissions =
    identity.membership?.permissions ||
    identity.current_membership?.permissions ||
    identity.currentMembership?.permissions ||
    [];

  const rolePermissions = Array.isArray(identity.roles)
    ? identity.roles.flatMap((role) => role?.permissions || [])
    : [];

  return [directPermissions, membershipPermissions, rolePermissions]
    .flat()
    .map(normalizePermissionCode)
    .filter(Boolean);
}

export const usePermissionStore = create((set, get) => ({
  permissions: [],
  isLoading: false,
  isLoaded: false,
  error: null,

  setPermissions: (permissions = []) =>
    set({
      permissions: permissions.map(normalizePermissionCode).filter(Boolean),
      isLoading: false,
      isLoaded: true,
      error: null,
    }),

  setPermissionsFromIdentity: (identity) =>
    set({
      permissions: extractPermissionsFromIdentity(identity),
      isLoading: false,
      isLoaded: true,
      error: null,
    }),

  resetPermissions: () =>
    set({ permissions: [], isLoading: false, isLoaded: true, error: null }),

  loadPermissions: async () => {
    set({ isLoading: true, error: null });

    try {
      const identity = await fetchIdentity();
      const permissions = extractPermissionsFromIdentity(identity);

      set({ permissions, isLoading: false, isLoaded: true, error: null });
      return permissions;
    } catch (error) {
      set({
        permissions: [],
        isLoading: false,
        isLoaded: true,
        error: error?.message || "Не удалось настроить доступный функционал",
      });
      return [];
    }
  },

  hasPermission: (permission) =>
    get().permissions.includes(normalizePermissionCode(permission)),
  hasAnyPermission: (requiredPermissions = []) =>
    requiredPermissions.some((permission) =>
      get().permissions.includes(normalizePermissionCode(permission)),
    ),
  hasAllPermissions: (requiredPermissions = []) =>
    requiredPermissions.every((permission) =>
      get().permissions.includes(normalizePermissionCode(permission)),
    ),
}));
