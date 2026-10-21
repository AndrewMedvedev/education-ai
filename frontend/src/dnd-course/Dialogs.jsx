import { useId, useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { countLabel, getLessonBlocks, MAX_CONTENT_BLOCKS, WORDS } from "./helpers";
import Icon, { Spinner } from "./icons";
import { canFinish, getProblems, getStats } from "./selectors";
import { useDndCourseStore } from "./store";
import { Modal } from "./ui";

export function ModuleDialog() {
  const dialog = useDndCourseStore((state) => state.moduleDialog);
  const allLessons = useDndCourseStore((state) => state.lessons);
  const allModules = useDndCourseStore((state) => state.modules);
  const lessons = useMemo(
    () =>
      allLessons.map((lesson) => ({
        id: lesson.id,
        title: lesson.title,
        moduleTitle: allModules.find((module) => module.lessonIds.includes(lesson.id))?.title || null,
      })),
    [allLessons, allModules],
  );
  const busy = useDndCourseStore((state) => Boolean(state.pending["create-module"]));
  const update = useDndCourseStore((state) => state.updateModuleDialog);
  const close = useDndCourseStore((state) => state.closeModuleDialog);
  const submit = useDndCourseStore((state) => state.submitModuleDialog);
  const id = useId();
  if (!dialog) return null;

  const selected = dialog.lessonIds;
  const visibleLessons = dialog.pick ? lessons : lessons.filter((lesson) => selected.includes(lesson.id));
  const toggle = (lessonId) =>
    update({
      lessonIds: selected.includes(lessonId) ? selected.filter((item) => item !== lessonId) : [...selected, lessonId],
    });
  const titleMissing = Boolean(dialog.error) && !dialog.title.trim();
  const descriptionMissing = Boolean(dialog.error) && !dialog.description.trim();

  return (
    <Modal
      title="Новый модуль"
      description="Модуль объединяет уроки. После создания выбранные уроки будут перенесены в него."
      onClose={close}
      closeDisabled={busy}
      footer={
        <>
          <button type="button" className="dnd-btn dnd-btn--ghost" onClick={close} disabled={busy}>
            Отмена
          </button>
          <button type="submit" form={`${id}-form`} className="dnd-btn dnd-btn--solid" disabled={busy || !selected.length} aria-busy={busy}>
            {busy ? <Spinner size={14} /> : <Icon name="check" size={16} />}
            {busy ? "Создаём модуль…" : "Создать модуль"}
          </button>
        </>
      }
    >
      <form
        id={`${id}-form`}
        className="dnd-stack"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className={`dnd-field ${titleMissing ? "has-error" : ""}`}>
          <label htmlFor={`${id}-title`}>
            Название<span aria-hidden="true"> *</span>
          </label>
          <input
            id={`${id}-title`}
            value={dialog.title}
            onChange={(event) => update({ title: event.target.value })}
            aria-required="true"
            aria-invalid={titleMissing || undefined}
            aria-describedby={dialog.error ? `${id}-error` : undefined}
            disabled={busy}
            maxLength={200}
          />
        </div>
        <div className={`dnd-field ${descriptionMissing ? "has-error" : ""}`}>
          <label htmlFor={`${id}-description`}>
            Описание<span aria-hidden="true"> *</span>
          </label>
          <textarea
            id={`${id}-description`}
            rows={3}
            value={dialog.description}
            onChange={(event) => update({ description: event.target.value })}
            aria-required="true"
            aria-invalid={descriptionMissing || undefined}
            aria-describedby={dialog.error ? `${id}-error` : undefined}
            disabled={busy}
          />
        </div>
        <div className="dnd-field">
          <label htmlFor={`${id}-goals`}>Цели обучения</label>
          <textarea
            id={`${id}-goals`}
            rows={3}
            value={dialog.learningObjectives}
            onChange={(event) => update({ learningObjectives: event.target.value })}
            placeholder="Каждая цель с новой строки"
            disabled={busy}
          />
        </div>
        <fieldset className="dnd-fieldset">
          <legend>Уроки модуля ({selected.length})</legend>
          {visibleLessons.length ? (
            <ul className="dnd-check-list nowheel">
              {visibleLessons.map((lesson) => (
                <li key={lesson.id}>
                  <label>
                    <input type="checkbox" checked={selected.includes(lesson.id)} onChange={() => toggle(lesson.id)} disabled={busy} />
                    <span title={lesson.title}>{lesson.title}</span>
                    {lesson.moduleTitle ? <small>сейчас в «{lesson.moduleTitle}»</small> : <small>без модуля</small>}
                  </label>
                </li>
              ))}
            </ul>
          ) : (
            <p className="dnd-muted">Сначала создайте хотя бы один урок из материалов.</p>
          )}
        </fieldset>
        {dialog.error ? (
          <p id={`${id}-error`} className="dnd-inline-error" role="alert">
            <Icon name="alert" size={16} />
            <span>{dialog.error}</span>
          </p>
        ) : null}
      </form>
    </Modal>
  );
}

export function MaterialPickerDialog() {
  const picker = useDndCourseStore((state) => state.materialPicker);
  const materials = useDndCourseStore(
    useShallow((state) => state.materials.filter((item) => item.status === "ready" && !item.lessonId)),
  );
  const busy = useDndCourseStore((state) => Boolean(state.pending["create-lesson"]));
  const toggle = useDndCourseStore((state) => state.toggleMaterialPick);
  const close = useDndCourseStore((state) => state.closeMaterialPicker);
  const createLesson = useDndCourseStore((state) => state.createLessonFromMaterials);
  if (!picker) return null;
  const selected = picker.selected;
  const overLimit = selected.length > MAX_CONTENT_BLOCKS;

  return (
    <Modal
      title="Новый урок"
      description="Отметьте материалы в том порядке, в котором они должны идти в уроке."
      onClose={close}
      closeDisabled={busy}
      footer={
        <>
          <button type="button" className="dnd-btn dnd-btn--ghost" onClick={close} disabled={busy}>
            Отмена
          </button>
          <button
            type="button"
            className="dnd-btn dnd-btn--solid"
            disabled={busy || !selected.length || overLimit}
            onClick={async () => {
              const created = await createLesson(selected);
              if (created) close();
            }}
          >
            {busy ? <Spinner size={14} /> : <Icon name="check" size={16} />}
            {busy ? "Создаём урок…" : "Объединить в урок"}
          </button>
        </>
      }
    >
      {materials.length ? (
        <ul className="dnd-check-list nowheel">
          {materials.map((item) => {
            const order = selected.indexOf(item.id);
            return (
              <li key={item.id}>
                <label>
                  <input type="checkbox" checked={order >= 0} onChange={() => toggle(item.id)} disabled={busy} />
                  <span title={item.fileName}>{item.fileName}</span>
                  {order >= 0 ? <small className="dnd-order-num">{order + 1}</small> : null}
                </label>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="dnd-muted">Нет свободных готовых материалов. Загрузите документы или дождитесь окончания обработки.</p>
      )}
      {overLimit ? (
        <p className="dnd-inline-error" role="alert">
          <Icon name="alert" size={16} />В одном уроке может быть не больше {MAX_CONTENT_BLOCKS} блоков.
        </p>
      ) : null}
    </Modal>
  );
}

export function FinishDialog({ onCreateCourse }) {
  const open = useDndCourseStore((state) => state.finishOpen);
  const snapshot = useDndCourseStore(
    useShallow((state) => ({
      course: state.course,
      materials: state.materials,
      lessons: state.lessons,
      modules: state.modules,
      forms: state.forms,
      pending: state.pending,
      saveStatus: state.saveStatus,
    })),
  );
  const stats = useMemo(() => getStats(snapshot), [snapshot]);
  const problems = useMemo(() => getProblems(snapshot), [snapshot]);
  const finishable = useMemo(() => canFinish(snapshot), [snapshot]);
  const busy = useDndCourseStore((state) => Boolean(state.pending.finish));
  const error = useDndCourseStore((state) => state.finishError);
  const close = useDndCourseStore((state) => state.closeFinish);
  const finish = useDndCourseStore((state) => state.finish);
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const requestFocus = useDndCourseStore((state) => state.requestFocus);
  const lessonsWithoutContent = useDndCourseStore(
    (state) => state.lessons.filter((lesson) => getLessonBlocks(lesson).length === 0).length,
  );
  if (!open) return null;

  const attention = problems.filter((item) => item.severity !== "info").length;
  const blocking = !finishable;

  return (
    <Modal
      title={blocking ? "Структура ещё не готова" : "Курс готов"}
      onClose={close}
      closeDisabled={busy}
      size="md"
      footer={
        <>
          <button type="button" className="dnd-btn dnd-btn--ghost" onClick={close} disabled={busy}>
            Вернуться к редактированию
          </button>
          <button
            type="button"
            className="dnd-btn dnd-btn--accent"
            onClick={() => finish(onCreateCourse)}
            disabled={busy || blocking}
            aria-busy={busy}
          >
            {busy ? <Spinner size={14} /> : <Icon name="flag" size={16} />}
            {busy ? "Открываем курс…" : error ? "Повторить" : "Завершить и посмотреть курс"}
          </button>
        </>
      }
    >
      <dl className="dnd-stats dnd-stats--summary">
        <div><dt>Модули</dt><dd>{countLabel(stats.modules, WORDS.module)}</dd></div>
        <div><dt>Уроки</dt><dd>{countLabel(stats.lessons, WORDS.lesson)}</dd></div>
        <div><dt>Материалы</dt><dd>{countLabel(stats.materials, WORDS.material)}</dd></div>
        <div className={attention ? "is-warn" : "is-ok"}>
          <dt>Требуют внимания</dt>
          <dd>{attention ? countLabel(attention, WORDS.item) : "нет"}</dd>
        </div>
      </dl>
      {blocking ? (
        <p className="dnd-inline-error" role="alert">
          <Icon name="alert" size={16} />
          <span>
            {stats.nonEmptyModules === 0
              ? "Чтобы завершить, нужен хотя бы один модуль с уроком."
              : "Дождитесь окончания сохранения и обработки документов."}
          </span>
        </p>
      ) : null}
      {problems.length || lessonsWithoutContent ? (
        <ul className="dnd-problems nowheel">
          {problems.map((problem) => (
            <li key={problem.id} className={`is-${problem.severity}`}>
              <Icon name={problem.severity === "info" ? "info" : "alert"} size={15} />
              <span>{problem.text}</span>
              {problem.nodeId ? (
                <button
                  type="button"
                  className="dnd-link dnd-link--sm"
                  onClick={() => {
                    close();
                    openInspector(problem.nodeId);
                    requestFocus([problem.nodeId]);
                  }}
                >
                  Показать
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="dnd-muted">
          <Icon name="check" size={15} /> Проблем не найдено.
        </p>
      )}
      <p className="dnd-muted dnd-finish-note">
        Некритичные замечания не мешают завершению. Уроки без модуля не попадут в курс. Из просмотра курса можно в любой момент вернуться на холст и доделать.
      </p>
      {error ? (
        <p className="dnd-inline-error" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </p>
      ) : null}
    </Modal>
  );
}
