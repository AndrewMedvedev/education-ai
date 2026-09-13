import { create } from "zustand";
import {
  createModel as createModelApi,
  deleteModel as deleteModelApi,
  fetchModelsPage,
} from "../utils/api";

const DEFAULT_PAGE = 1;
const DEFAULT_PAGE_SIZE = 10;

const initialState = {
  items: [],
  page: DEFAULT_PAGE,
  size: DEFAULT_PAGE_SIZE,
  total: 0,
  totalPages: 1,
  isLoading: false,
  isCreating: false,
  deletingUid: null,
  error: "",
  notice: "",
  validationErrors: {},
  selectedModel: null,
  createForm: {
    name: "",
    description: "",
    context: "",
  },
};

function getErrorMessage(error, fallback) {
  return error?.userMessage || error?.message || fallback;
}

export const useModelStore = create((set, get) => ({
  ...initialState,

  setPage: (page) => set({ page }),

  setSelectedModel: (selectedModel) => set({ selectedModel }),

  setNotice: (notice) => set({ notice }),

  clearMessages: () => set({ error: "", notice: "" }),

  updateCreateField: (field, value) =>
    set((state) => ({
      createForm: { ...state.createForm, [field]: value },
      validationErrors: { ...state.validationErrors, [field]: "", form: "" },
    })),

  resetCreateForm: () =>
    set({
      createForm: initialState.createForm,
      validationErrors: {},
    }),

  fetchModels: async (page = get().page, size = get().size) => {
    set({ isLoading: true, error: "" });

    try {
      const response = await fetchModelsPage({ page, size });
      set({
        items: response.items || [],
        page: response.page || page,
        size: response.size || size,
        total: response.total_items ?? response.total ?? 0,
        totalPages: response.total_pages || 1,
        isLoading: false,
        error: "",
      });
      return response;
    } catch (error) {
      set({
        items: [],
        total: 0,
        totalPages: 1,
        isLoading: false,
        error: getErrorMessage(error, "Не удалось загрузить AI-модели."),
      });
      throw error;
    }
  },

  createModel: async (payload) => {
    const name = payload?.name?.trim();

    if (!name) {
      set({ validationErrors: { name: "Укажите название модели." } });
      return null;
    }

    set({ isCreating: true, error: "", notice: "", validationErrors: {} });

    try {
      const model = await createModelApi({ ...payload, name });
      set({
        createForm: initialState.createForm,
        isCreating: false,
        notice: "AI-модель создана.",
        validationErrors: {},
      });
      await get().fetchModels(1, get().size);
      return model;
    } catch (error) {
      set({
        isCreating: false,
        validationErrors: error?.validationErrors || {},
        error: getErrorMessage(error, "Не удалось создать AI-модель."),
      });
      throw error;
    }
  },

  deleteModel: async (uid) => {
    if (!uid || get().deletingUid) return null;

    set({ deletingUid: uid, error: "", notice: "" });

    try {
      await deleteModelApi(uid);
      set({
        items: get().items.filter((item) => item.uid !== uid),
        deletingUid: null,
        selectedModel: null,
        notice: "AI-модель удалена.",
      });
      await get().fetchModels(get().page, get().size);
      return true;
    } catch (error) {
      if (error?.status === 404) {
        set({
          items: get().items.filter((item) => item.uid !== uid),
          deletingUid: null,
          selectedModel: null,
          notice: "AI-модель уже была удалена.",
        });
        return true;
      }

      set({
        deletingUid: null,
        error: getErrorMessage(error, "Не удалось удалить AI-модель."),
      });
      throw error;
    }
  },

  reset: () => set(initialState),
}));
