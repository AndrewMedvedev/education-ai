export function buildManualCourse({ title, modules, lessons, blocks, courseId }) {
  const courseBlocks = modules.map((module, moduleIndex) => {
    const moduleLessons = lessons.filter((lesson) =>
      module.lessonIds.includes(lesson.id),
    );

    const courseLessons = moduleLessons.map((lesson) => {
      const markdown = blocks
        .filter(
          (block) =>
            lesson.blockIds.includes(block.id) && block.status === "ready",
        )
        .map((block) => block.markdown)
        .filter(Boolean)
        .join("\n\n---\n\n");

      return {
        id: lesson.id,
        title: lesson.title,
        duration: "Материал урока",
        summary: "",
        content: "",
        markdown,
      };
    });

    return {
      id: `${courseId}-block-${moduleIndex + 1}`,
      title: module.title,
      description: "",
      duration: `${courseLessons.length} уроков`,
      learningObjectives: [],
      lessons: courseLessons,
      practice: [
        {
          id: `${courseId}-block-${moduleIndex + 1}-practice-1`,
          title: `Практика по модулю ${moduleIndex + 1}`,
          duration: "Практика",
          brief: "",
          result: "",
          markdown: "",
        },
      ],
    };
  });

  const totalLessons = courseBlocks.reduce(
    (total, block) => total + block.lessons.length,
    0,
  );

  return {
    id: courseId,
    title: (title || "").trim() || "Новый курс",
    category: "Создан вручную",
    description: "",
    duration: `${courseBlocks.length} модулей`,
    lessons: `${totalLessons} уроков`,
    level: "Для старта",
    format: "Собственные материалы",
    tags: [],
    learningObjectives: [],
    blocks: courseBlocks,
  };
}
