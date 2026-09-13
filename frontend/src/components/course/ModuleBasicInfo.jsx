export default function ModuleBasicInfo({ module }) {
  if (!module) {
    return (
      <article className="course-viewer-card">
        <p className="course-viewer-muted">
          Выберите модуль, чтобы увидеть описание.
        </p>
      </article>
    );
  }

  const learningObjectives = Array.isArray(module.learningObjectives)
    ? module.learningObjectives
    : Array.isArray(module.learning_objectives)
      ? module.learning_objectives
      : [];

  return (
    <article className="course-viewer-card module-basic-info">
      <div className="course-viewer-eyebrow">Модуль {module.order + 1}</div>
      <h2>{module.title}</h2>
      {module.description ? (
        <p className="course-viewer-description">{module.description}</p>
      ) : (
        <p className="course-viewer-muted">Описание модуля отсутствует.</p>
      )}

      {learningObjectives.length > 0 ? (
        <div className="course-info-section">
          <h3>Цели модуля</h3>
          <ul className="course-viewer-list">
            {learningObjectives.map((objective, index) => (
              <li key={`${module.id}-objective-${index}`}>{objective}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="course-viewer-muted">Цели модуля пока не указаны.</p>
      )}
    </article>
  );
}
