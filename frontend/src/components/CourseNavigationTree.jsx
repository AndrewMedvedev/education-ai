export default function CourseNavigationTree({
  selectedCourse,
  selectedBlock,
  selectedLessonId,
  selectedPracticeId,
  completedLessons,
  completedPractices,
  openBlock,
  openLesson,
  openPractice,
  mode = "theory",
}) {
  const isPracticeMode = mode === "practice";
  const isMetricsMode = mode === "metrics";
  const completedItems = selectedCourse.blocks.reduce(
    (total, block) =>
      total +
      (isPracticeMode
        ? block.practice.filter((practice) => completedPractices[practice.id])
            .length
        : block.lessons.filter((lesson) => completedLessons[lesson.id]).length),
    0,
  );
  const totalItems = selectedCourse.blocks.reduce(
    (total, block) =>
      total + (isPracticeMode ? block.practice.length : block.lessons.length),
    0,
  );
  const progressLabel = isMetricsMode
    ? "Метрики"
    : isPracticeMode
      ? "Практика"
      : "Теория";

  const openBlockInCurrentMode = (block) => {
    if (isPracticeMode && block.practice[0]) {
      openPractice(block.practice[0].id);
      return;
    }

    openBlock(block.id);
  };

  return (
    <aside className="course-nav-tree" aria-label="Навигация по курсу">
      <div className="course-nav-tree-head">
        <strong>{selectedCourse.title}</strong>
        <span>
          {isMetricsMode
            ? "Выбор урока"
            : `${progressLabel}: ${completedItems}/${totalItems}`}
        </span>
      </div>
      <ul className="course-nav-block-list">
        {selectedCourse.blocks.map((block, blockIndex) => (
          <li
            key={block.id}
            className={`course-nav-block ${selectedBlock.id === block.id ? "is-active" : ""}`}
          >
            <button
              type="button"
              className="course-nav-block-btn"
              onClick={() => openBlockInCurrentMode(block)}
            >
              <span>{blockIndex + 1}</span>
              <strong>{block.title}</strong>
            </button>
            <ul className="course-nav-item-list">
              {isPracticeMode
                ? block.practice.map((practice, practiceIndex) => (
                    <li key={practice.id}>
                      <button
                        type="button"
                        className={`course-nav-item-btn course-nav-practice-btn ${selectedPracticeId === practice.id ? "is-active" : ""}`}
                        onClick={() => openPractice(practice.id)}
                      >
                        <span className="course-nav-item-number">
                          P{blockIndex + 1}.{practiceIndex + 1}
                        </span>
                        <span className="course-nav-item-title">
                          {practice.title}
                        </span>
                        <span
                          className={`course-nav-item-status ${completedPractices[practice.id] ? "is-done" : ""}`}
                        />
                      </button>
                    </li>
                  ))
                : block.lessons.map((lesson, lessonIndex) => (
                    <li key={lesson.id}>
                      <button
                        type="button"
                        className={`course-nav-item-btn ${selectedLessonId === lesson.id ? "is-active" : ""}`}
                        onClick={() => openLesson(lesson.id)}
                      >
                        <span className="course-nav-item-number">
                          {blockIndex + 1}.{lessonIndex + 1}
                        </span>
                        <span className="course-nav-item-title">
                          {lesson.title}
                        </span>
                        {!isMetricsMode && (
                          <span
                            className={`course-nav-item-status ${completedLessons[lesson.id] ? "is-done" : ""}`}
                          />
                        )}
                      </button>
                    </li>
                  ))}
            </ul>
          </li>
        ))}
      </ul>
    </aside>
  );
}
