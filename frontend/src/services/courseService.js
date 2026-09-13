import {
  fetchCourses,
  getCourseBasicInfo as fetchCourseBasicInfo,
  getLessonBasicInfo,
  getLessonTheory,
  getModuleBasicInfo,
} from "../utils/api";
import { getMyCourses, signCourse } from "./studentApi";

const ENROLLMENT_PAGE_SIZE = 100;
const courseCache = new Map();
const moduleCache = new Map();
const lessonCache = new Map();
const lessonTheoryCache = new Map();

function replaceModule(course, module) {
  return {
    ...course,
    blocks: (course.blocks || []).map((block) =>
      block.id === module.id ? { ...block, ...module } : block,
    ),
  };
}

function replaceLessonInCourse(course, lesson) {
  return {
    ...course,
    blocks: (course.blocks || []).map((block) => ({
      ...block,
      lessons: (block.lessons || []).map((item) =>
        item.id === lesson.id ? { ...item, ...lesson } : item,
      ),
    })),
  };
}

function rememberCourse(course) {
  if (course?.id) {
    courseCache.set(course.id, course);
  }
  return course;
}

export async function getCourse(courseId) {
  if (courseId && courseCache.has(courseId)) {
    return courseCache.get(courseId);
  }

  const courses = await fetchCourses({ page: 1, size: 20 });
  courses.forEach(rememberCourse);
  const course = courseId
    ? courses.find((item) => item.id === courseId)
    : courses[0];

  if (!course) {
    throw new Error("Курс не найден");
  }

  return course;
}

export async function getCourseBasicInfo(courseId) {
  if (!courseId) {
    return getCourse();
  }
  if (courseCache.has(courseId)) {
    return courseCache.get(courseId);
  }
  return rememberCourse(await fetchCourseBasicInfo(courseId));
}

export async function getCourseLearningStructure(courseId) {
  const course = await getCourseBasicInfo(courseId);
  for (const moduleRef of course.blocks || []) {
    if (!moduleCache.has(moduleRef.id)) {
      const module = await getModuleById(moduleRef.id);
      rememberCourse(
        replaceModule(courseCache.get(course.id) || course, module),
      );
    }
  }
  return courseCache.get(course.id) || course;
}

export async function getModuleById(moduleId) {
  if (moduleCache.has(moduleId)) {
    return moduleCache.get(moduleId);
  }

  const module = await getModuleBasicInfo(moduleId);
  moduleCache.set(moduleId, module);
  for (const [courseId, course] of courseCache.entries()) {
    if ((course.blocks || []).some((block) => block.id === moduleId)) {
      courseCache.set(courseId, replaceModule(course, module));
    }
  }
  return module;
}

export async function getLessonById(lessonId) {
  if (lessonCache.has(lessonId)) {
    return lessonCache.get(lessonId);
  }

  const lesson = await getLessonBasicInfo(lessonId);
  lessonCache.set(lessonId, lesson);
  for (const [courseId, course] of courseCache.entries()) {
    courseCache.set(courseId, replaceLessonInCourse(course, lesson));
  }
  return lesson;
}

export async function getLessonContentBlocks(lessonId) {
  if (!lessonId) {
    return [];
  }

  if (lessonTheoryCache.has(lessonId)) {
    return lessonTheoryCache.get(lessonId);
  }

  const contentBlocks = await getLessonTheory(lessonId);
  lessonTheoryCache.set(lessonId, contentBlocks);

  const lesson = lessonCache.get(lessonId);
  if (lesson) {
    lessonCache.set(lessonId, {
      ...lesson,
      contentBlocks,
    });
  }

  return contentBlocks;
}

export async function isUserEnrolled(courseId) {
  if (!courseId) {
    return false;
  }

  const courses = await getMyCourses({ page: 1, size: ENROLLMENT_PAGE_SIZE });
  return courses.items.some((course) => course.id === courseId);
}

export async function enrollUserToCourse(courseId) {
  if (!courseId) {
    throw new Error("Невозможно записаться: идентификатор курса отсутствует");
  }

  return signCourse(courseId);
}
