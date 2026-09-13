function TextList({ title, items, emptyText }) {
  if (!Array.isArray(items) || items.length === 0) {
    return <p className="course-viewer-muted">{emptyText}</p>;
  }

  return (
    <div className="course-info-section">
      <h3>{title}</h3>
      <ul className="course-viewer-list">
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function CourseBasicInfo({ course }) {
  if (!course) {
    return (
      <p className="course-viewer-muted">Информация о курсе недоступна.</p>
    );
  }

  const modules = Array.isArray(course.blocks)
    ? course.blocks
    : Array.isArray(course.modules)
      ? course.modules
      : [];
  const learningObjectives = Array.isArray(course.learningObjectives)
    ? course.learningObjectives
    : Array.isArray(course.learning_objectives)
      ? course.learning_objectives
      : [];
  const difficulty = course.difficulty || course.level || "Не указан";

  return (
    <article className="course-viewer-card course-basic-info">
      <div className="course-viewer-eyebrow">Курс</div>
      <h1>{course.title}</h1>
      {course.description ? (
        <p className="course-viewer-description">{course.description}</p>
      ) : (
        <p className="course-viewer-muted">Описание курса пока отсутствует.</p>
      )}

      <div className="course-meta-grid">
        <div>
          <span>Уровень</span>
          <strong>{difficulty}</strong>
        </div>
        <div>
          <span>Модулей</span>
          <strong>{modules.length}</strong>
        </div>
      </div>

      {course.tags?.length > 0 && (
        <div className="course-tags" aria-label="Теги курса">
          {course.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      )}

      <TextList
        title="Цели обучения"
        items={learningObjectives}
        emptyText="Цели обучения пока не указаны."
      />
    </article>
  );
}
