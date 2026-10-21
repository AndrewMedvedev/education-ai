import {
  PROGRESS_STATUS_LABELS,
  getLessonProgressStatus,
} from "../../services/progressService";

export default function LessonList({
  lessons,
  selectedLessonId,
  onSelectLesson,
  progressById = null,
}) {
  if (!Array.isArray(lessons) || lessons.length === 0) {
    return (
      <article className="course-viewer-card course-viewer-side-card">
        <h2>Уроки</h2>
        <p className="course-viewer-muted">
          В выбранном модуле пока нет уроков.
        </p>
      </article>
    );
  }

  return (
    <article className="course-viewer-card course-viewer-side-card">
      <h2>Уроки модуля</h2>
      <ul className="course-pick-list">
        {lessons.map((lesson) => {
          const isSelected = lesson.id === selectedLessonId;
          const status = progressById
            ? getLessonProgressStatus(progressById[lesson.id])
            : null;

          return (
            <li key={lesson.id}>
              <button
                type="button"
                className={`course-pick-item ${isSelected ? "is-selected" : ""} ${status ? `has-progress is-${status}` : ""}`}
                onClick={() => onSelectLesson(lesson.id)}
              >
                <span className="course-pick-order">
                  {String(lesson.order + 1).padStart(2, "0")}
                </span>
                <span>{lesson.title}</span>
                {status && (
                  <span className={`course-pick-progress is-${status}`}>
                    {PROGRESS_STATUS_LABELS[status]}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </article>
  );
}
