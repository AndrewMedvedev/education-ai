export function getLessonSequence(course) {
  return course.blocks.flatMap((block) =>
    block.lessons.map((lesson) => ({
      blockId: block.id,
      lessonId: lesson.id,
      lessonTitle: lesson.title,
    })),
  );
}

export function getBlockProgress(block, completedLessons, completedPractices) {
  const completedLessonsInBlock = block.lessons.filter(
    (lesson) => completedLessons[lesson.id],
  ).length;
  const completedPracticesInBlock = (block.practice || []).filter(
    (practice) => completedPractices[practice.id],
  ).length;
  const totalItemsInBlock = block.lessons.length + (block.practice || []).length;
  const completedInBlock = completedLessonsInBlock + completedPracticesInBlock;
  const blockProgressPercent = totalItemsInBlock
    ? Math.round((completedInBlock / totalItemsInBlock) * 100)
    : 0;

  return {
    completedLessonsInBlock,
    completedPracticesInBlock,
    totalItemsInBlock,
    completedInBlock,
    blockProgressPercent,
  };
}

export function getOverallProgress(courses, completedLessons, completedPractices) {
  const totalLessonsCount = courses.reduce(
    (total, course) =>
      total +
      course.blocks.reduce((sum, block) => sum + block.lessons.length, 0),
    0,
  );
  const totalPracticesCount = courses.reduce(
    (total, course) =>
      total +
      course.blocks.reduce((sum, block) => sum + block.practice.length, 0),
    0,
  );
  const completedLessonsCount = Object.values(completedLessons).filter(Boolean)
    .length;
  const completedPracticesCount = Object.values(completedPractices).filter(
    Boolean,
  ).length;
  const totalProgressItems = totalLessonsCount + totalPracticesCount;
  const overallProgressPercent = totalProgressItems
    ? Math.round(
        ((completedLessonsCount + completedPracticesCount) / totalProgressItems) *
          100,
      )
    : 0;

  return {
    totalLessonsCount,
    totalPracticesCount,
    completedLessonsCount,
    completedPracticesCount,
    totalProgressItems,
    overallProgressPercent,
  };
}

export function getCourseProgress(course, completedLessons, completedPractices) {
  const total = course.blocks.reduce(
    (sum, block) => sum + block.lessons.length + block.practice.length,
    0,
  );
  const completed = course.blocks.reduce(
    (sum, block) =>
      sum +
      block.lessons.filter((lesson) => completedLessons[lesson.id]).length +
      block.practice.filter((practice) => completedPractices[practice.id]).length,
    0,
  );
  const progress = Math.round((completed / Math.max(1, total)) * 100);

  return { total, completed, progress };
}
