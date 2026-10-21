import { useEffect, useRef } from "react";
import {
  PROGRESS_STATUS_LABELS,
  getLessonProgressStatus,
  getModuleProgressSummary,
} from "../services/progressService";

const LESSON_PARTS = [
  { key: "theoryCompletedAt", label: "Теория" },
  { key: "practiceCompletedAt", label: "Практика" },
  { key: "testCompletedAt", label: "Проверочные вопросы" },
];

// Одна точка на урок: серая — не начат, жёлтая — пройден частично,
// зелёная — пройдены теория, практика и проверочные вопросы.
function LessonProgressMark({ progress }) {
  const status = getLessonProgressStatus(progress);
  const details = LESSON_PARTS.map(
    (part) => `${part.label}: ${progress?.[part.key] ? "пройдено" : "нет"}`,
  ).join(", ");

  return (
    <span
      className={`course-nav-progress-dot is-${status}`}
      title={`${PROGRESS_STATUS_LABELS[status]}. ${details}`}
      aria-label={`${PROGRESS_STATUS_LABELS[status]}. ${details}`}
    />
  );
}

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
  // Прогресс ученика с backend: { [lessonId]: LessonProgress | null } и сводка курса.
  lessonProgressById = null,
  progressSummary = null,
}) {
  const isPracticeMode = mode === "practice";
  const isMetricsMode = mode === "metrics";
  const hasProgress =
    !isPracticeMode && !isMetricsMode && Boolean(lessonProgressById);
  const treeRef = useRef(null);
  const selectedBlockId = selectedBlock?.id;

  // Держим выбранный урок (или модуль) в зоне видимости дерева, а не сбрасываем
  // прокрутку дерева в начало при открытии урока.
  useEffect(() => {
    const tree = treeRef.current;
    if (!tree) return;
    const activeItem =
      tree.querySelector(".course-nav-item-btn.is-active") ||
      tree.querySelector(".course-nav-block.is-active .course-nav-block-btn");
    if (!activeItem) return;

    const treeRect = tree.getBoundingClientRect();
    const itemRect = activeItem.getBoundingClientRect();
    const margin = 24;
    if (
      itemRect.top < treeRect.top + margin ||
      itemRect.bottom > treeRect.bottom - margin
    ) {
      tree.scrollTop +=
        itemRect.top - treeRect.top - (treeRect.height - itemRect.height) / 2;
    }
  }, [selectedLessonId, selectedPracticeId, selectedBlockId]);
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
    <aside
      ref={treeRef}
      className="course-nav-tree"
      aria-label="Навигация по курсу"
    >
      <div className="course-nav-tree-head">
        <strong>{selectedCourse.title}</strong>
        {hasProgress ? (
          <div className="course-nav-progress">
            <div className="course-nav-progress-row">
              <span>
                Пройдено уроков: {progressSummary?.completed ?? 0}/
                {progressSummary?.total ?? 0}
              </span>
              <b>{progressSummary?.percent ?? 0}%</b>
            </div>
            <div
              className="course-nav-progress-bar"
              role="progressbar"
              aria-label="Прогресс курса"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressSummary?.percent ?? 0}
            >
              <span style={{ width: `${progressSummary?.percent ?? 0}%` }} />
            </div>
          </div>
        ) : (
          <span>
            {isMetricsMode
              ? "Выбор урока"
              : `${progressLabel}: ${completedItems}/${totalItems}`}
          </span>
        )}
      </div>
      <ul className="course-nav-block-list">
        {selectedCourse.blocks.map((block, blockIndex) => {
          const moduleProgress = hasProgress
            ? getModuleProgressSummary(block, lessonProgressById)
            : null;

          return (
            <li
              key={block.id}
              className={`course-nav-block ${selectedBlock.id === block.id ? "is-active" : ""} ${moduleProgress ? `has-progress is-${moduleProgress.status}` : ""}`}
            >
              <button
                type="button"
                className={`course-nav-block-btn ${moduleProgress ? "has-progress" : ""}`}
                onClick={() => openBlockInCurrentMode(block)}
              >
                <span>{blockIndex + 1}</span>
                <strong>{block.title}</strong>
                {moduleProgress && moduleProgress.total > 0 && (
                  <em
                    className={`course-nav-block-progress is-${moduleProgress.status}`}
                    title={PROGRESS_STATUS_LABELS[moduleProgress.status]}
                  >
                    {moduleProgress.completed}/{moduleProgress.total}
                  </em>
                )}
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
                          className={`course-nav-item-btn ${selectedLessonId === lesson.id ? "is-active" : ""} ${hasProgress ? `has-progress is-${getLessonProgressStatus(lessonProgressById[lesson.id])}` : ""}`}
                          onClick={() => openLesson(lesson.id)}
                        >
                          <span className="course-nav-item-number">
                            {blockIndex + 1}.{lessonIndex + 1}
                          </span>
                          <span className="course-nav-item-title">
                            {lesson.title}
                          </span>
                          {hasProgress ? (
                            <LessonProgressMark
                              progress={lessonProgressById[lesson.id]}
                            />
                          ) : (
                            !isMetricsMode && (
                              <span
                                className={`course-nav-item-status ${completedLessons[lesson.id] ? "is-done" : ""}`}
                              />
                            )
                          )}
                        </button>
                      </li>
                    ))}
              </ul>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
