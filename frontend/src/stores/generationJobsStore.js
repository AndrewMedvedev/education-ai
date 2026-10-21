import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { getLocalStorage } from "../utils/storage";

/**
 * Запущенные генерации модулей и уроков из редактора курса.
 * На backend нет статуса задачи по task_id, поэтому фронт отслеживает результат сам:
 * перечитывает курс (модуль) или модуль (урок), пока не появится новый элемент.
 *
 * jobs[key] = {
 *   key, kind: "module" | "lesson", courseId, moduleId, order, taskId, chatKey,
 *   knownIds: string[], startedAt, status: "running" | "done" | "error",
 *   resultId, resultTitle, lessonsCount, lastChangeAt, error
 * }
 */

const MEMORY_STORAGE = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

export const generationJobKey = (kind, courseId, contextId = "") =>
  [kind, courseId, contextId].join(":");

export const useGenerationJobsStore = create(
  persist(
    (set, get) => ({
      jobs: {},

      startJob: (job) =>
        set((state) => ({
          jobs: {
            ...state.jobs,
            [job.key]: {
              status: "running",
              resultId: null,
              resultTitle: "",
              lessonsCount: 0,
              lastChangeAt: null,
              error: "",
              startedAt: new Date().toISOString(),
              knownIds: [],
              ...job,
            },
          },
        })),

      updateJob: (key, patch) =>
        set((state) =>
          state.jobs[key]
            ? {
                jobs: {
                  ...state.jobs,
                  [key]: { ...state.jobs[key], ...patch },
                },
              }
            : {},
        ),

      removeJob: (key) =>
        set((state) => {
          if (!state.jobs[key]) return {};
          const jobs = { ...state.jobs };
          delete jobs[key];
          return { jobs };
        }),

      getJob: (key) => get().jobs[key] || null,
    }),
    {
      name: "ai-course-generation-jobs-v1",
      version: 1,
      storage: createJSONStorage(() => getLocalStorage() || MEMORY_STORAGE),
      partialize: (state) => ({ jobs: state.jobs }),
    },
  ),
);
