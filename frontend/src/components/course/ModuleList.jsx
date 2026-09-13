export default function ModuleList({ modules, selectedModuleId, disabled, onSelectModule }) {
  if (!Array.isArray(modules) || modules.length === 0) {
    return (
      <article className="course-viewer-card course-viewer-side-card">
        <h2>Модули</h2>
        <p className="course-viewer-muted">В курсе пока нет модулей.</p>
      </article>
    );
  }

  return (
    <article className="course-viewer-card course-viewer-side-card">
      <h2>Модули</h2>
      {disabled && (
        <p className="course-viewer-muted">
          Содержимое модулей станет доступно после записи на курс.
        </p>
      )}
      <ul className="course-pick-list">
        {modules.map((module) => {
          const isSelected = module.id === selectedModuleId;

          return (
            <li key={module.id}>
              <button
                type="button"
                className={`course-pick-item ${isSelected ? "is-selected" : ""}`}
                onClick={() => onSelectModule(module.id)}
                disabled={disabled}
              >
                <span className="course-pick-order">
                  {String(module.order + 1).padStart(2, "0")}
                </span>
                <span>{module.title}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </article>
  );
}
