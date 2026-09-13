import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  authenticateWithMembership,
  fetchIdentity,
  fetchCurrentUser,
  updateCurrentUser,
  login as loginApi,
  logout as logoutApi,
  readStoredSession,
  saveStoredSession,
  setTokenChangeHandler,
  setUnauthorizedHandler,
  isTokenExpired,
} from "../utils/api";
import { attachmentsApi } from "../utils/attachments";
import { getMediaId, getMediaUrl, MEDIA_FOLDERS } from "../utils/media";

const initialStoredSession = readStoredSession();
const SESSION_CACHE_STORAGE_KEY = "aicolab-session-cache";
const SESSION_CACHE_VERSION = 1;
let identityRequestPromise = null;
let currentUserRequestPromise = null;

const initialState = {
  accessToken: initialStoredSession.accessToken,
  refreshToken: initialStoredSession.refreshToken,
  expiresAt: initialStoredSession.expiresAt,
  membershipId: initialStoredSession.membershipId,
  organizationId: initialStoredSession.organizationId,
  authenticationToken: null,
  memberships: [],
  identity: null,
  user: null,
  loginStep: "credentials",
  isLoading: false,
  error: null,
  validationErrors: {},
  hasHydrated: false,
};

function getSessionUserId(user) {
  return user?.id || user?.user_id || user?.userId || "";
}

function normalizeSessionUser(user) {
  if (!user || typeof user !== "object") return user;
  const userId = getSessionUserId(user);
  const avatarId = getMediaId(user.avatar_url || user.avatarUrl);
  return {
    ...user,
    avatar_url: avatarId || user.avatar_url || "",
    avatarUrl: getMediaUrl(userId, MEDIA_FOLDERS.AVATAR, avatarId),
  };
}

function getOrganizationIdFromMembership(membership) {
  return (
    membership?.organization_id ||
    membership?.organizationId ||
    membership?.organization?.id ||
    membership?.organization?.organization_id ||
    membership?.organization?.organizationId ||
    null
  );
}

function getMembershipIdFromIdentity(identity) {
  return (
    identity?.membership_id ||
    identity?.membershipId ||
    identity?.membership?.id ||
    identity?.current_membership?.id ||
    identity?.currentMembership?.id ||
    null
  );
}

function getOrganizationIdFromIdentity(identity) {
  return (
    identity?.organization_id ||
    identity?.organizationId ||
    identity?.organization?.id ||
    identity?.organization?.organization_id ||
    identity?.organization?.organizationId ||
    identity?.membership?.organization_id ||
    identity?.membership?.organizationId ||
    identity?.membership?.organization?.id ||
    identity?.current_membership?.organization_id ||
    identity?.current_membership?.organization?.id ||
    identity?.currentMembership?.organizationId ||
    identity?.currentMembership?.organization?.id ||
    null
  );
}

function decodeJwtExp(token) {
  if (!token || typeof token !== "string") return null;

  try {
    const encodedPayload = token.split(".")[1] || "";
    const base64Payload = encodedPayload
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(encodedPayload.length / 4) * 4, "=");
    const payload = JSON.parse(atob(base64Payload));
    return Number(payload?.exp) || null;
  } catch {
    return null;
  }
}

function normalizeExpiresAt(value, accessToken) {
  if (value === null || value === undefined || value === "") {
    return decodeJwtExp(accessToken);
  }

  const numericValue = Number(value);
  if (Number.isFinite(numericValue) && numericValue > 0) {
    return numericValue > 9999999999
      ? Math.floor(numericValue / 1000)
      : numericValue;
  }

  const parsedDate = Date.parse(value);
  if (Number.isFinite(parsedDate)) {
    return Math.floor(parsedDate / 1000);
  }

  return decodeJwtExp(accessToken);
}

function normalizeTokens(tokens) {
  const source = tokens?.tokens || tokens?.data || tokens || {};
  const accessToken =
    source.access_token || source.accessToken || source.access;
  const refreshToken =
    source.refresh_token || source.refreshToken || source.refresh;
  const expiresAt =
    source.expires_at ||
    source.expiresAt ||
    source.exp ||
    source.access_expires_at ||
    source.accessTokenExpiresAt;

  return {
    accessToken,
    refreshToken,
    expiresAt: normalizeExpiresAt(expiresAt, accessToken),
  };
}

export const useSessionStore = create(
  persist(
    (set, get) => ({
      ...initialState,

      // Флаг не персистится: он отражает завершение гидратации в текущей вкладке.
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),

      get isAuthenticated() {
        const state = get();
        return Boolean(
          state.accessToken &&
          state.expiresAt &&
          (!isTokenExpired(state.expiresAt) || state.refreshToken),
        );
      },

      setTokens: (tokens, context = {}) => {
        const normalizedTokens = normalizeTokens(tokens);
        const nextSession = {
          accessToken: normalizedTokens.accessToken || get().accessToken,
          refreshToken: normalizedTokens.refreshToken || get().refreshToken,
          expiresAt: normalizedTokens.expiresAt || get().expiresAt,
          membershipId: context.membershipId || get().membershipId,
          organizationId: context.organizationId || get().organizationId,
        };

        saveStoredSession(nextSession);
        set({
          accessToken: nextSession.accessToken,
          refreshToken: nextSession.refreshToken,
          expiresAt: nextSession.expiresAt,
          membershipId: nextSession.membershipId,
          organizationId: nextSession.organizationId,
        });
      },

      loginWithCredentials: async ({ email, password }) => {
        set({ isLoading: true, error: null, validationErrors: {} });

        try {
          const data = await loginApi({ email, password });
          set({
            authenticationToken: data.authentication_token,
            memberships: Array.isArray(data.memberships)
              ? data.memberships
              : [],
            loginStep: "organization",
            isLoading: false,
            error: null,
            validationErrors: {},
          });
          return data;
        } catch (error) {
          set({
            isLoading: false,
            error:
              error.status === 401
                ? "Неверный email или пароль."
                : error.userMessage || error.message || "Не удалось войти.",
            validationErrors: error.validationErrors || {},
          });
          throw error;
        }
      },

      selectMembership: async (membershipId) => {
        const { authenticationToken, memberships, setTokens, loadIdentity } =
          get();
        const membership = memberships.find(
          (item) =>
            item?.id === membershipId || item?.membership_id === membershipId,
        );
        const normalizedMembershipId =
          membership?.id || membership?.membership_id || membershipId;
        const organizationId = getOrganizationIdFromMembership(membership);

        if (!authenticationToken) {
          const error = new Error(
            "Сессия выбора организации истекла. Войдите заново.",
          );
          set({ error: error.message, loginStep: "credentials" });
          throw error;
        }

        set({ isLoading: true, error: null, validationErrors: {} });

        try {
          const tokens = await authenticateWithMembership({
            authentication_token: authenticationToken,
            membership_id: normalizedMembershipId,
          });
          setTokens(tokens, {
            membershipId: normalizedMembershipId,
            organizationId,
          });
          set({
            authenticationToken: null,
            memberships: [],
            loginStep: "credentials",
          });
          const identity = await loadIdentity();
          if (!identity) {
            const error = new Error(
              "Не удалось подтвердить сессию выбранной организации.",
            );
            set({ isLoading: false, error: error.message });
            throw error;
          }

          get().loadCurrentUser();
          set({ isLoading: false });
          return tokens;
        } catch (error) {
          const isExpiredSelection = error.status === 401;
          set({
            isLoading: false,
            error: isExpiredSelection
              ? "Сессия выбора организации истекла. Войдите заново."
              : error.userMessage ||
                error.message ||
                "Не удалось выбрать организацию.",
            validationErrors: error.validationErrors || {},
            authenticationToken: isExpiredSelection
              ? null
              : authenticationToken,
            memberships: isExpiredSelection ? [] : memberships,
            loginStep: isExpiredSelection ? "credentials" : "organization",
          });
          throw error;
        }
      },

      loadIdentity: async () => {
        if (!get().accessToken) return null;
        if (identityRequestPromise) return identityRequestPromise;

        identityRequestPromise = fetchIdentity()
          .then((identity) => {
            set({
              identity,
              membershipId:
                getMembershipIdFromIdentity(identity) || get().membershipId,
              organizationId:
                getOrganizationIdFromIdentity(identity) || get().organizationId,
            });
            return identity;
          })
          .catch((error) => {
            if (error.status === 401) {
              get().clearSession();
              return null;
            }

            set({
              identity: null,
              error:
                error.userMessage ||
                error.message ||
                "Не удалось загрузить данные текущей сессии.",
            });
            return null;
          })
          .finally(() => {
            identityRequestPromise = null;
          });

        return identityRequestPromise;
      },

      loadCurrentUser: async () => {
        if (!get().accessToken) return null;
        if (currentUserRequestPromise) return currentUserRequestPromise;

        currentUserRequestPromise = fetchCurrentUser()
          .then((user) => {
            const normalizedUser = normalizeSessionUser(user);
            set({ user: normalizedUser });
            return normalizedUser;
          })
          .catch((error) => {
            set({
              user: null,
              error:
                error.status === 401
                  ? null
                  : error.userMessage ||
                    error.message ||
                    "Не удалось загрузить профиль пользователя.",
            });
            return null;
          })
          .finally(() => {
            currentUserRequestPromise = null;
          });

        return currentUserRequestPromise;
      },

      resetOrganizationSelection: () =>
        set({
          authenticationToken: null,
          memberships: [],
          loginStep: "credentials",
          error: null,
          validationErrors: {},
        }),

      updateProfile: async (changes) => {
        set({ isLoading: true, error: null, validationErrors: {} });

        try {
          const user = normalizeSessionUser(await updateCurrentUser(changes));
          set({ user, isLoading: false, error: null, validationErrors: {} });
          return user;
        } catch (error) {
          set({
            isLoading: false,
            error:
              error.userMessage ||
              error.message ||
              "Не удалось обновить профиль.",
            validationErrors: error.validationErrors || {},
          });
          throw error;
        }
      },

      uploadAvatar: async (file) => {
        set({ isLoading: true, error: null, validationErrors: {} });

        try {
          const currentUser = get().user || (await get().loadCurrentUser());
          const ownerId = getSessionUserId(currentUser);
          const attachment = await attachmentsApi.uploadAttachment(
            file,
            MEDIA_FOLDERS.AVATAR,
            ownerId,
            { folder: MEDIA_FOLDERS.AVATAR },
          );
          const avatarId = getMediaId(
            attachment?.storage_key ||
              attachment?.storageKey ||
              attachment?.file_id ||
              attachment?.fileId ||
              attachment?.image_id ||
              attachment?.imageId ||
              attachment?.id ||
              attachment?.attachment_id,
          );
          const avatarUrl = getMediaUrl(
            ownerId,
            MEDIA_FOLDERS.AVATAR,
            avatarId,
          );
          const user = normalizeSessionUser(
            await updateCurrentUser({ avatarUrl }),
          );
          const userWithAvatarUrl = {
            ...user,
            avatar_url: avatarId,
            avatarUrl,
          };
          set({
            user: userWithAvatarUrl,
            isLoading: false,
            error: null,
            validationErrors: {},
          });
          return userWithAvatarUrl;
        } catch (error) {
          set({
            isLoading: false,
            error:
              error.userMessage ||
              error.message ||
              "Не удалось загрузить аватар.",
            validationErrors: error.validationErrors || {},
          });
          throw error;
        }
      },

      clearPersistedState: () => useSessionStore.persist.clearStorage(),

      clearSession: () => {
        identityRequestPromise = null;
        currentUserRequestPromise = null;
        saveStoredSession(null);
        set({
          accessToken: null,
          refreshToken: null,
          expiresAt: null,
          membershipId: null,
          organizationId: null,
          authenticationToken: null,
          memberships: [],
          identity: null,
          user: null,
          loginStep: "credentials",
          isLoading: false,
          error: null,
          validationErrors: {},
        });
        // set() сначала записывает очищенное состояние, затем удаляем сам ключ,
        // чтобы localStorage не накапливал пустые записи между сессиями.
        get().clearPersistedState();
      },

      logout: async () => {
        const { accessToken, refreshToken, clearSession } = get();

        try {
          if (accessToken && refreshToken) {
            await logoutApi({
              access_token: accessToken,
              refresh_token: refreshToken,
            });
          }
        } catch {
          // Локальная очистка обязательна даже если сервер не ответил или уже отозвал токены.
        } finally {
          clearSession();
        }
      },
    }),
    {
      name: SESSION_CACHE_STORAGE_KEY,
      version: SESSION_CACHE_VERSION,
      // Токены, identity, ошибки и промежуточные данные логина намеренно исключены.
      partialize: (state) => ({
        user: state.user,
        membershipId: state.membershipId,
      }),
      migrate: (persistedState, version) => {
        if (version !== SESSION_CACHE_VERSION) {
          return { user: null, membershipId: null };
        }

        return persistedState;
      },
      merge: (persistedState, currentState) => {
        const cache = persistedState || {};
        const belongsToCurrentMembership =
          Boolean(currentState.membershipId) &&
          cache.membershipId === currentState.membershipId;

        return {
          ...currentState,
          // Не показываем профиль от другой организации/сессии.
          user: belongsToCurrentMembership ? cache.user || null : null,
        };
      },
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    },
  ),
);

setTokenChangeHandler((session) => {
  useSessionStore.setState({
    accessToken: session.accessToken,
    refreshToken: session.refreshToken,
    expiresAt: session.expiresAt,
    membershipId: session.membershipId,
    organizationId: session.organizationId,
  });
});

setUnauthorizedHandler(() => {
  useSessionStore.getState().clearSession();
});
