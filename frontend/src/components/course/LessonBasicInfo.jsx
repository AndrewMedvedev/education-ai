export default function LessonBasicInfo({ lesson }) {
  if (!lesson) {
    return (
      <article className="course-viewer-card">
        <p className="course-viewer-muted">
          Выберите урок, чтобы увидеть описание.
        </p>
      </article>
    );
  }

  const learningObjectives = Array.isArray(lesson.learningObjectives)
    ? lesson.learningObjectives
    : Array.isArray(lesson.learning_objectives)
      ? lesson.learning_objectives
      : [];

  return (
    <article className="course-viewer-card lesson-basic-info">
      <div className="course-viewer-eyebrow">Урок {lesson.order + 1}</div>
      <h2>{lesson.title}</h2>
      {lesson.description ? (
        <p className="course-viewer-description">{lesson.description}</p>
      ) : (
        <p className="course-viewer-muted">Описание урока отсутствует.</p>
      )}

      <div className="course-meta-grid">
        <div>
          <span>Время</span>
          <strong>
            {lesson.estimated_time_minutes === null
              ? "Не указано"
              : `${lesson.estimated_time_minutes} мин.`}
          </strong>
        </div>
      </div>

      {learningObjectives.length > 0 ? (
        <div className="course-info-section">
          <h3>Цели урока</h3>
          <ul className="course-viewer-list">
            {learningObjectives.map((objective, index) => (
              <li key={`${lesson.id}-objective-${index}`}>{objective}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="course-viewer-muted">Цели урока пока не указаны.</p>
      )}
    </article>
  );
}
