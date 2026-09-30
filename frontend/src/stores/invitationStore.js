import { create } from "zustand";
import {
  cancelInvitation as cancelInvitationRequest,
  getCourseInvitations,
  IS_INVITATION_MOCK,
  inviteToCourse,
  resendInvitation as resendInvitationRequest,
} from "../services/invitationApi";

/**
 * Стор карты приглашений курса.
 *
 * Состояние разложено по courseId — блок живёт в карточке конкретного курса.
 * Отправка приглашения оптимистичная: запись появляется со статусом pending
 * сразу, а при ошибке запроса откатывается.
 */

const EMPTY_INVITATIONS = [];

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizeEmail(email));
}

function withoutId(set, id) {
  return new Set([...set].filter((item) => item !== id));
}

export const useInvitationStore = create((set, get) => ({
  invitationsByCourse: {},
  loadingCourseIds: new Set(),
  pendingInvitationIds: new Set(),
  errorByCourse: {},

  getInvitations: (courseId) => get().invitationsByCourse[courseId] || EMPTY_INVITATIONS,

  isLoading: (courseId) => get().loadingCourseIds.has(courseId),

  getError: (courseId) => get().errorByCourse[courseId] || "",

  isInvitationPending: (invitationId) =>
    get().pendingInvitationIds.has(invitationId),

  loadInvitations: async (courseId, options = {}) => {
    if (!courseId) return null;

    set((state) => ({
      loadingCourseIds: new Set([...state.loadingCourseIds, courseId]),
      errorByCourse: { ...state.errorByCourse, [courseId]: "" },
    }));

    try {
      const page = await getCourseInvitations(courseId, {}, options);
      set((state) => ({
        invitationsByCourse: {
          ...state.invitationsByCourse,
          [courseId]: page.items,
        },
        loadingCourseIds: withoutId(state.loadingCourseIds, courseId),
      }));
      return page;
    } catch (error) {
      if (options.signal?.aborted) {
        set((state) => ({
          loadingCourseIds: withoutId(state.loadingCourseIds, courseId),
        }));
        return null;
      }

      set((state) => ({
        loadingCourseIds: withoutId(state.loadingCourseIds, courseId),
        errorByCourse: {
          ...state.errorByCourse,
          [courseId]:
            error?.userMessage ||
            error?.message ||
            "Не удалось загрузить приглашения.",
        },
      }));
      throw error;
    }
  },

  sendInvitation: async (courseId, { email, role }, { currentUserEmail } = {}) => {
    const normalizedEmail = normalizeEmail(email);

    if (!courseId) return null;
    if (!normalizedEmail) throw new Error("Укажите email приглашаемого.");
    if (!isValidEmail(normalizedEmail)) throw new Error("Некорректный email.");
    if (!role) throw new Error("Выберите роль.");
    if (currentUserEmail && normalizeEmail(currentUserEmail) === normalizedEmail) {
      throw new Error("Нельзя пригласить себя.");
    }
    if (
      get()
        .getInvitations(courseId)
        .some((invitation) => normalizeEmail(invitation.email) === normalizedEmail)
    ) {
      throw new Error("Этот email уже приглашён в курс.");
    }

    if (IS_INVITATION_MOCK) {
      // Демо-режим: создание недоступно — запись не добавляем даже оптимистично,
      // сразу пробрасываем понятную ошибку в форму.
      return inviteToCourse(courseId, { email: normalizedEmail, role });
    }

    const optimisticId = `pending-${Date.now()}`;
    const optimisticInvitation = {
      id: optimisticId,
      email: normalizedEmail,
      role,
      status: "pending",
      createdAt: new Date().toISOString(),
      invitedBy: "",
    };

    set((state) => ({
      invitationsByCourse: {
        ...state.invitationsByCourse,
        [courseId]: [
          ...(state.invitationsByCourse[courseId] || EMPTY_INVITATIONS),
          optimisticInvitation,
        ],
      },
      pendingInvitationIds: new Set([
        ...state.pendingInvitationIds,
        optimisticId,
      ]),
      errorByCourse: { ...state.errorByCourse, [courseId]: "" },
    }));

    try {
      const created = await inviteToCourse(courseId, {
        email: normalizedEmail,
        role,
      });
      const savedInvitation = created?.id
        ? { ...optimisticInvitation, ...created, id: created.id }
        : optimisticInvitation;

      set((state) => ({
        invitationsByCourse: {
          ...state.invitationsByCourse,
          [courseId]: (state.invitationsByCourse[courseId] || []).map(
            (invitation) =>
              invitation.id === optimisticId ? savedInvitation : invitation,
          ),
        },
        pendingInvitationIds: withoutId(state.pendingInvitationIds, optimisticId),
      }));
      return savedInvitation;
    } catch (error) {
      const message =
        error?.userMessage || error?.message || "Не удалось отправить приглашение.";

      set((state) => ({
        invitationsByCourse: {
          ...state.invitationsByCourse,
          [courseId]: (state.invitationsByCourse[courseId] || []).filter(
            (invitation) => invitation.id !== optimisticId,
          ),
        },
        pendingInvitationIds: withoutId(state.pendingInvitationIds, optimisticId),
        errorByCourse: { ...state.errorByCourse, [courseId]: message },
      }));
      throw error;
    }
  },

  resendInvitation: async (courseId, invitationId) => {
    if (!courseId || !invitationId || get().isInvitationPending(invitationId)) {
      return null;
    }

    set((state) => ({
      pendingInvitationIds: new Set([
        ...state.pendingInvitationIds,
        invitationId,
      ]),
      errorByCourse: { ...state.errorByCourse, [courseId]: "" },
    }));

    try {
      const updated = await resendInvitationRequest(courseId, invitationId);

      set((state) => ({
        invitationsByCourse: {
          ...state.invitationsByCourse,
          [courseId]: (state.invitationsByCourse[courseId] || []).map(
            (invitation) =>
              invitation.id === invitationId
                ? {
                    ...invitation,
                    status: "pending",
                    createdAt:
                      updated?.createdAt ||
                      invitation.createdAt ||
                      new Date().toISOString(),
                  }
                : invitation,
          ),
        },
        pendingInvitationIds: withoutId(state.pendingInvitationIds, invitationId),
      }));
      return updated;
    } catch (error) {
      const message =
        error?.userMessage ||
        error?.message ||
        "Не удалось отправить приглашение повторно.";

      set((state) => ({
        pendingInvitationIds: withoutId(state.pendingInvitationIds, invitationId),
        errorByCourse: { ...state.errorByCourse, [courseId]: message },
      }));
      throw error;
    }
  },

  cancelInvitation: async (courseId, invitationId) => {
    if (!courseId || !invitationId || get().isInvitationPending(invitationId)) {
      return null;
    }

    const current = get().invitationsByCourse[courseId] || EMPTY_INVITATIONS;
    const removed = current.find((invitation) => invitation.id === invitationId);

    set((state) => ({
      invitationsByCourse: {
        ...state.invitationsByCourse,
        [courseId]: (state.invitationsByCourse[courseId] || []).filter(
          (invitation) => invitation.id !== invitationId,
        ),
      },
      pendingInvitationIds: new Set([
        ...state.pendingInvitationIds,
        invitationId,
      ]),
      errorByCourse: { ...state.errorByCourse, [courseId]: "" },
    }));

    try {
      await cancelInvitationRequest(courseId, invitationId);
      set((state) => ({
        pendingInvitationIds: withoutId(state.pendingInvitationIds, invitationId),
      }));
    } catch (error) {
      const message =
        error?.userMessage || error?.message || "Не удалось отменить приглашение.";

      set((state) => ({
        invitationsByCourse: {
          ...state.invitationsByCourse,
          [courseId]: removed
            ? [...(state.invitationsByCourse[courseId] || []), removed]
            : state.invitationsByCourse[courseId] || EMPTY_INVITATIONS,
        },
        pendingInvitationIds: withoutId(state.pendingInvitationIds, invitationId),
        errorByCourse: { ...state.errorByCourse, [courseId]: message },
      }));
      throw error;
    }
  },
}));
