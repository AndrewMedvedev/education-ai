import { useId } from "react";
import { DIFFICULTY_OPTIONS } from "./constants";
import Icon, { Spinner } from "./icons";
import { useDndCourseStore } from "./store";

const STEPS = [
  { icon: "course", title: "Основа курса", text: "Название, описание, сложность и теги" },
  { icon: "upload", title: "Материалы", text: "Документы превращаются в карточки на холсте" },
  { icon: "lesson", title: "Уроки", text: "Перетаскивайте материалы в уроки" },
  { icon: "module", title: "Модули", text: "Собирайте уроки в модули и завершайте" },
];

export default function StartScreen() {
  const form = useDndCourseStore((state) => state.courseForm);
  const error = useDndCourseStore((state) => state.courseError);
  const notice = useDndCourseStore((state) => state.courseNotice);
  const leftovers = useDndCourseStore((state) => state.materials.length + state.lessons.length);
  const resetAll = useDndCourseStore((state) => state.resetAll);
  const busy = useDndCourseStore((state) => Boolean(state.pending.course));
  const setCourseForm = useDndCourseStore((state) => state.setCourseForm);
  const createCourse = useDndCourseStore((state) => state.createCourse);
  const id = useId();
  const errorId = `${id}-error`;
  const titleMissing = Boolean(error) && !form.title.trim();
  const descriptionMissing = Boolean(error) && !form.description.trim();

  return (
    <section className="dnd-start" aria-labelledby={`${id}-title`}>
      <div className="dnd-start-intro">
        <span className="dnd-eyebrow">Drag &amp; Drop курс</span>
        <h1 id={`${id}-title`}>Создайте основу курса</h1>
        {notice ? (
          <div className="dnd-inline-error dnd-start-notice" role="alert">
            <Icon name="alert" size={16} />
            <span>{notice}</span>
            {leftovers ? (
              <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => resetAll()}>
                Очистить черновик
              </button>
            ) : null}
          </div>
        ) : null}
        <p>
          Сначала сохраним карточку курса — без неё сервер не примет материалы. Затем откроется холст: загружайте документы,
          перетаскивайте их в уроки, а уроки — в модули.
        </p>
        <ol className="dnd-start-steps">
          {STEPS.map((step, index) => (
            <li key={step.title} className={index === 0 ? "is-current" : ""}>
              <span className="dnd-start-step-icon">
                <Icon name={step.icon} size={18} />
              </span>
              <span>
                <strong>{step.title}</strong>
                <small>{step.text}</small>
              </span>
            </li>
          ))}
        </ol>
      </div>

      <form
        className="dnd-start-form"
        noValidate
        aria-describedby={error ? errorId : undefined}
        onSubmit={(event) => {
          event.preventDefault();
          createCourse();
        }}
      >
        <div className={`dnd-field ${titleMissing ? "has-error" : ""}`}>
          <label htmlFor={`${id}-name`}>
            Название курса<span aria-hidden="true"> *</span>
          </label>
          <input
            id={`${id}-name`}
            value={form.title}
            onChange={(event) => setCourseForm({ title: event.target.value })}
            placeholder="Например: Основы Python для аналитиков"
            aria-required="true"
            aria-invalid={titleMissing || undefined}
            aria-describedby={titleMissing ? errorId : undefined}
            maxLength={200}
            disabled={busy}
            autoFocus
          />
        </div>
        <div className={`dnd-field ${descriptionMissing ? "has-error" : ""}`}>
          <label htmlFor={`${id}-description`}>
            Описание<span aria-hidden="true"> *</span>
          </label>
          <textarea
            id={`${id}-description`}
            value={form.description}
            onChange={(event) => setCourseForm({ description: event.target.value })}
            placeholder="Кратко опишите, чему научится студент"
            rows={4}
            aria-required="true"
            aria-invalid={descriptionMissing || undefined}
            aria-describedby={descriptionMissing ? errorId : undefined}
            disabled={busy}
          />
        </div>
        <div className="dnd-start-grid">
          <div className="dnd-field">
            <label htmlFor={`${id}-difficulty`}>Сложность</label>
            <select
              id={`${id}-difficulty`}
              value={form.difficulty}
              onChange={(event) => setCourseForm({ difficulty: event.target.value })}
              disabled={busy}
            >
              {DIFFICULTY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="dnd-field">
            <label htmlFor={`${id}-tags`}>Теги</label>
            <input
              id={`${id}-tags`}
              value={form.tags}
              onChange={(event) => setCourseForm({ tags: event.target.value })}
              placeholder="python, backend, junior"
              aria-describedby={`${id}-tags-hint`}
              disabled={busy}
            />
            <small id={`${id}-tags-hint`} className="dnd-field-hint">
              Через запятую
            </small>
          </div>
        </div>
        {error ? (
          <p id={errorId} className="dnd-inline-error" role="alert">
            <Icon name="alert" size={16} />
            <span>{error}</span>
          </p>
        ) : null}
        <button type="submit" className="dnd-btn dnd-btn--accent dnd-btn--lg" disabled={busy} aria-busy={busy}>
          {busy ? <Spinner size={16} /> : <Icon name="arrowRight" size={18} />}
          {busy ? "Создаём курс…" : "Создать и открыть конструктор"}
        </button>
      </form>
    </section>
  );
}
