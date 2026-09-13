export const EMPTY_COURSE = {
  id: "",
  title: "Курс не выбран",
  description: "",
  category: "",
  duration: "",
  level: "",
  format: "",
  learningObjectives: [],
  blocks: [],
};

export const EMPTY_BLOCK = {
  id: "",
  title: "Модуль не выбран",
  lessons: [],
  practice: [],
  learningObjectives: [],
};

export const EMPTY_LESSON = {
  id: "",
  title: "Урок не выбран",
  duration: "",
  summary: "",
  content: "",
  markdown: "",
  contentBlocks: [],
};

export const mergeCourse = (courses, nextCourse) => {
  if (!nextCourse?.id) return courses;
  return courses.some((course) => course.id === nextCourse.id)
    ? courses.map((course) =>
        course.id === nextCourse.id
          ? {
              ...course,
              ...nextCourse,
              blocks: nextCourse.blocks?.length
                ? nextCourse.blocks
                : course.blocks,
            }
          : course,
      )
    : [...courses, nextCourse];
};

export const mergeCoursePage = (currentCourses, nextCourses) =>
  nextCourses.map((nextCourse) => {
    const currentCourse = currentCourses.find(
      (course) => course.id === nextCourse.id,
    );

    if (!currentCourse) return nextCourse;

    return mergeCourse([currentCourse], nextCourse)[0];
  });

export const mergeModule = (course, nextModule) => ({
  ...course,
  blocks: (course.blocks || []).map((block) =>
    block.id === nextModule.id
      ? {
          ...block,
          ...nextModule,
          lessons: nextModule.lessons?.length ? nextModule.lessons : block.lessons,
          practice: block.practice || [],
        }
      : block,
  ),
});

export const mergeLesson = (course, nextLesson) => ({
  ...course,
  blocks: (course.blocks || []).map((block) => ({
    ...block,
    lessons: (block.lessons || []).map((lesson) =>
      lesson.id === nextLesson.id ? { ...lesson, ...nextLesson } : lesson,
    ),
  })),
});

export function getSelectedCourse(courses, selectedCourseId) {
  return (
    courses.find((course) => course.id === selectedCourseId) ||
    courses[0] ||
    EMPTY_COURSE
  );
}

export function getSelectedBlock(course, selectedBlockId) {
  return (
    (course.blocks || []).find((block) => block.id === selectedBlockId) ||
    course.blocks?.[0] ||
    EMPTY_BLOCK
  );
}

export function getSelectedLesson(block, selectedLessonId) {
  return (
    (block.lessons || []).find((lesson) => lesson.id === selectedLessonId) ||
    block.lessons?.[0] ||
    EMPTY_LESSON
  );
}

export function getSelectedPractice(block, selectedPracticeId) {
  return (
    block.practice?.find((practice) => practice.id === selectedPracticeId) ||
    block.practice?.[0] ||
    null
  );
}

export function createEmptyCourseBlock(courseId) {
  const suffix = Date.now().toString(36);
  const blockId = `${courseId}-block-${suffix}`;
  const lessonId = `${blockId}-lesson-1`;

  return {
    id: blockId,
    block: {
      id: blockId,
      title: "Новый блок",
      description: "",
      duration: "2 недели",
      lessons: [
        {
          id: lessonId,
          title: "Новый урок",
          duration: "20 минут",
          summary: "",
          content: "",
          markdown: "Новый текстовый блок.",
          contentBlocks: [
            {
              content_type: "text",
              ai_generated: false,
              md_content: "Новый текстовый блок.",
            },
          ],
        },
      ],
      practice: [],
    },
  };
}

export const moveItem = (items, itemId, direction) => {
  const currentIndex = items.findIndex((item) => item.id === itemId);
  const nextIndex = currentIndex + direction;

  if (currentIndex < 0 || nextIndex < 0 || nextIndex >= items.length) {
    return items;
  }

  const nextItems = [...items];
  [nextItems[currentIndex], nextItems[nextIndex]] = [
    nextItems[nextIndex],
    nextItems[currentIndex],
  ];
  return nextItems;
};
