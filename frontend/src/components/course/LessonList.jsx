export default function LessonList({ lessons, selectedLessonId, onSelectLesson }) {
  if (!Array.isArray(lessons) || lessons.length === 0) {
    return (
      <article className="course-viewer-card course-viewer-side-card">
        <h2>Уроки</h2>
        <p className="course-viewer-muted">В выбранном модуле пока нет уроков.</p>
      </article>
    );
  }

  return (
    <article className="course-viewer-card course-viewer-side-card">
      <h2>Уроки модуля</h2>
      <ul className="course-pick-list">
        {lessons.map((lesson) => {
          const isSelected = lesson.id === selectedLessonId;

          return (
            <li key={lesson.id}>
              <button
                type="button"
                className={`course-pick-item ${isSelected ? "is-selected" : ""}`}
                onClick={() => onSelectLesson(lesson.id)}
              >
                <span className="course-pick-order">
                  {String(lesson.order + 1).padStart(2, "0")}
                </span>
                <span>{lesson.title}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </article>
  );
}
