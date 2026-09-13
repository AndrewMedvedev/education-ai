import { create } from "zustand";
import { getMyCourses, signCourse } from "../services/studentApi";

const DEFAULT_MY_COURSES_META = {
  page: 1,
  size: 10,
  total: 0,
  pages: 1,
  total_pages: 1,
  has_next: false,
  has_prev: false,
};

function getCourseStudentIds(course) {
  return (course?.students || [])
    .map((student) => student?.course_id || student?.courseId || course?.id)
    .filter(Boolean);
}

export const useStudentStore = create((set, get) => ({
  myCourses: [],
  myCoursesMeta: DEFAULT_MY_COURSES_META,
  isMyCoursesLoading: false,
  myCoursesError: "",
  enrolledCourseIds: new Set(),
  signingCourseIds: new Set(),

  isCourseEnrolled: (courseId) => get().enrolledCourseIds.has(courseId),
  isCourseSigning: (courseId) => get().signingCourseIds.has(courseId),

  loadMyCourses: async ({ page = 1, size = 10 } = {}, options = {}) => {
    set({ isMyCoursesLoading: true, myCoursesError: "" });

    try {
      const response = await getMyCourses({ page, size }, options);
      const loadedCourseIds = response.items.flatMap(getCourseStudentIds);

      set((state) => ({
        myCourses: response.items,
        myCoursesMeta: {
          page: response.page || page,
          size: response.size || size,
          total: response.total || 0,
          pages: response.pages || response.total_pages || 1,
          total_pages: response.total_pages || response.pages || 1,
          has_next: Boolean(response.has_next),
          has_prev: Boolean(response.has_prev),
        },
        enrolledCourseIds: new Set([
          ...state.enrolledCourseIds,
          ...response.items.map((course) => course.id).filter(Boolean),
          ...loadedCourseIds,
        ]),
        isMyCoursesLoading: false,
      }));
      return response;
    } catch (error) {
      if (options.signal?.aborted) {
        set({ isMyCoursesLoading: false });
        return null;
      }

      const message = error?.userMessage || error?.message || "Не удалось загрузить ваши курсы.";
      set({
        myCourses: [],
        myCoursesError: message,
        isMyCoursesLoading: false,
      });
      throw error;
    }
  },

  signCourse: async (courseId) => {
    if (!courseId || get().signingCourseIds.has(courseId)) {
      return null;
    }

    set((state) => ({
      signingCourseIds: new Set([...state.signingCourseIds, courseId]),
      myCoursesError: "",
    }));

    try {
      const student = await signCourse(courseId);
      set((state) => ({
        enrolledCourseIds: new Set([...state.enrolledCourseIds, courseId]),
        myCourses: state.myCourses.map((course) =>
          course.id === courseId
            ? { ...course, students: [...(course.students || []), student] }
            : course,
        ),
        signingCourseIds: new Set(
          [...state.signingCourseIds].filter((id) => id !== courseId),
        ),
      }));
      return student;
    } catch (error) {
      set((state) => ({
        signingCourseIds: new Set(
          [...state.signingCourseIds].filter((id) => id !== courseId),
        ),
        myCoursesError:
          error?.userMessage || error?.message || "Не удалось записаться на курс.",
      }));
      throw error;
    }
  },
}));
