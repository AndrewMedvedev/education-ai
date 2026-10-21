import { useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { MATERIAL_STATUS } from "./constants";
import { countLabel, getLessonBlocks, MAX_CONTENT_BLOCKS, nodeId, WORDS } from "./helpers";
import Icon from "./icons";
import { useDndCourseStore } from "./store";
import { ActionMenu, StatusPill, useDndActions } from "./ui";

function moduleMenu(lessonIds, currentModuleId) {
  const state = useDndCourseStore.getState();
  return [
    {
      key: "new",
      icon: "plus",
      label: lessonIds.length > 1 ? `Новый модуль из ${lessonIds.length} уроков` : "Новый модуль…",
      onSelect: () => state.openModuleDialog(lessonIds),
    },
    ...[...state.modules]
      .sort((a, b) => a.order - b.order)
      .map((module) => ({
        key: module.id,
        icon: "module",
        label: module.title,
        disabled: module.id === currentModuleId,
        onSelect: async () => {
          for (const id of lessonIds) {
            // eslint-disable-next-line no-await-in-loop
            await useDndCourseStore.getState().moveLessonToModule(id, module.id);
          }
        },
      })),
  ];
}

function LessonRow({ lesson, index, total, moduleId }) {
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const moveLessonBy = useDndCourseStore((state) => state.moveLessonBy);
  const toggleSelected = useDndCourseStore((state) => state.toggleSelected);
  const selected = useDndCourseStore((state) => state.selectedIds.includes(nodeId.lesson(lesson.id)));
  const pending = useDndCourseStore((state) => Boolean(state.pending[nodeId.lesson(lesson.id)] || (moduleId && state.pending[`order:${moduleId}`])));
  const { requestDelete } = useDndActions();
  return (
    <li className={`dnd-list-row ${pending ? "is-pending" : ""}`}>
      {!moduleId ? (
        <input
          type="checkbox"
          checked={selected}
          onChange={() => toggleSelected(nodeId.lesson(lesson.id))}
          aria-label={`Выбрать урок «${lesson.title}»`}
        />
      ) : (
        <span className="dnd-order-num">{index + 1}</span>
      )}
      <button type="button" className="dnd-list-main" onClick={() => openInspector(nodeId.lesson(lesson.id), "main")}>
        <strong title={lesson.title}>{lesson.title}</strong>
        <small>
          {getLessonBlocks(lesson).length}/{MAX_CONTENT_BLOCKS} {WORDS.block[2]}
          {lesson.estimatedTimeMinutes ? ` · ${lesson.estimatedTimeMinutes} мин` : ""}
        </small>
      </button>
      <div className="dnd-list-actions">
        {moduleId ? (
          <>
            <button type="button" className="dnd-icon-btn dnd-icon-btn--sm" onClick={() => moveLessonBy(lesson.id, -1)} disabled={index === 0 || pending} aria-label={`Урок «${lesson.title}» выше`} title="Выше">
              <Icon name="arrowUp" size={15} />
            </button>
            <button type="button" className="dnd-icon-btn dnd-icon-btn--sm" onClick={() => moveLessonBy(lesson.id, 1)} disabled={index === total - 1 || pending} aria-label={`Урок «${lesson.title}» ниже`} title="Ниже">
              <Icon name="arrowDown" size={15} />
            </button>
          </>
        ) : null}
        <ActionMenu label="Переместить в модуль" icon="module" items={() => moduleMenu([lesson.id], moduleId)} buttonClassName="dnd-icon-btn dnd-icon-btn--sm" align="end" />
        <button type="button" className="dnd-icon-btn dnd-icon-btn--sm is-danger" onClick={() => requestDelete(nodeId.lesson(lesson.id))} aria-label={`Удалить урок «${lesson.title}»`} title="Удалить">
          <Icon name="trash" size={15} />
        </button>
      </div>
    </li>
  );
}

export default function ListView() {
  const materials = useDndCourseStore((state) => state.materials);
  const lessons = useDndCourseStore((state) => state.lessons);
  const modules = useDndCourseStore((state) => state.modules);
  const selectedIds = useDndCourseStore(useShallow((state) => state.selectedIds));
  const toggleSelected = useDndCourseStore((state) => state.toggleSelected);
  const setSelection = useDndCourseStore((state) => state.setSelection);
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const createLesson = useDndCourseStore((state) => state.createLessonFromMaterials);
  const openModuleDialog = useDndCourseStore((state) => state.openModuleDialog);
  const moveModuleBy = useDndCourseStore((state) => state.moveModuleBy);
  const retry = useDndCourseStore((state) => state.retryMaterial);
  const creatingLesson = useDndCourseStore((state) => Boolean(state.pending["create-lesson"]));
  const orderPending = useDndCourseStore((state) => Boolean(state.pending["order:modules"]));
  const { pickFiles, requestDelete } = useDndActions();

  const assigned = useMemo(() => new Set(modules.flatMap((module) => module.lessonIds)), [modules]);
  const freeLessons = lessons.filter((lesson) => !assigned.has(lesson.id));
  const orderedModules = [...modules].sort((a, b) => a.order - b.order);
  const lessonById = new Map(lessons.map((lesson) => [lesson.id, lesson]));
  const selectedMaterials = selectedIds.filter((id) => id.startsWith("material:")).map((id) => id.slice(9));
  const selectedLessons = selectedIds
    .filter((id) => id.startsWith("lesson:"))
    .map((id) => id.slice(7))
    .filter((id) => !assigned.has(id));

  return (
    <div className="dnd-list nowheel">
      <section className="dnd-list-section" aria-labelledby="dnd-list-materials">
        <header>
          <h2 id="dnd-list-materials">
            <Icon name="file" size={17} /> Материалы <small>{materials.length}</small>
          </h2>
          <button type="button" className="dnd-btn dnd-btn--solid dnd-btn--sm" onClick={() => pickFiles()}>
            <Icon name="upload" size={15} /> Загрузить
          </button>
        </header>
        {materials.length ? (
          <ul className="dnd-list-rows">
            {materials.map((material) => {
              const key = nodeId.material(material.id);
              const status = material.lessonId ? "used" : material.status;
              const selectable = material.status === "ready" && !material.lessonId;
              return (
                <li key={material.id} className={`dnd-list-row is-${status}`}>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(key)}
                    onChange={() => toggleSelected(key)}
                    disabled={!selectable}
                    aria-label={`Выбрать материал «${material.fileName}»`}
                  />
                  <button type="button" className="dnd-list-main" onClick={() => openInspector(key, "content")} disabled={material.status === "uploading"}>
                    <strong title={material.fileName}>
                      #{material.number} {material.fileName}
                    </strong>
                    <StatusPill tone={MATERIAL_STATUS[status]?.tone} busy={material.status === "uploading"} icon={status === "error" ? "alert" : null}>
                      {MATERIAL_STATUS[status]?.label}
                    </StatusPill>
                    {material.status === "error" ? <small className="dnd-node-error">{material.error}</small> : null}
                  </button>
                  <div className="dnd-list-actions">
                    {material.status === "error" ? (
                      <button
                        type="button"
                        className="dnd-icon-btn dnd-icon-btn--sm"
                        onClick={() => {
                          if (material.tooBig || !retry(material.id)) pickFiles({ replaceMaterialId: material.id });
                        }}
                        aria-label={`Повторить загрузку «${material.fileName}»`}
                        title="Повторить"
                      >
                        <Icon name="retry" size={15} />
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="dnd-icon-btn dnd-icon-btn--sm is-danger"
                      onClick={() => requestDelete(key)}
                      disabled={Boolean(material.lessonId) || material.status === "uploading"}
                      aria-label={`Удалить материал «${material.fileName}»`}
                      title="Удалить"
                    >
                      <Icon name="trash" size={15} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="dnd-muted">Загрузите документы — каждый станет материалом для урока.</p>
        )}
        {selectedMaterials.length ? (
          <div className="dnd-list-toolbar">
            <span>Выбрано: {countLabel(selectedMaterials.length, WORDS.material)}</span>
            <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => setSelection([])}>
              Снять выбор
            </button>
            <button
              type="button"
              className="dnd-btn dnd-btn--solid dnd-btn--sm"
              onClick={() => createLesson(selectedMaterials)}
              disabled={creatingLesson || selectedMaterials.length > MAX_CONTENT_BLOCKS}
            >
              <Icon name="lesson" size={15} /> Объединить в урок
            </button>
          </div>
        ) : null}
      </section>

      <section className="dnd-list-section" aria-labelledby="dnd-list-free">
        <header>
          <h2 id="dnd-list-free">
            <Icon name="lesson" size={17} /> Уроки без модуля <small>{freeLessons.length}</small>
          </h2>
        </header>
        {freeLessons.length ? (
          <ul className="dnd-list-rows">
            {freeLessons.map((lesson) => (
              <LessonRow key={lesson.id} lesson={lesson} index={0} total={1} moduleId={null} />
            ))}
          </ul>
        ) : (
          <p className="dnd-muted">Отметьте материалы и нажмите «Объединить в урок».</p>
        )}
        {selectedLessons.length ? (
          <div className="dnd-list-toolbar">
            <span>Выбрано: {countLabel(selectedLessons.length, WORDS.lesson)}</span>
            <button type="button" className="dnd-btn dnd-btn--solid dnd-btn--sm" onClick={() => openModuleDialog(selectedLessons)}>
              <Icon name="module" size={15} /> Объединить в модуль
            </button>
          </div>
        ) : null}
      </section>

      <section className="dnd-list-section" aria-labelledby="dnd-list-modules">
        <header>
          <h2 id="dnd-list-modules">
            <Icon name="module" size={17} /> Модули <small>{modules.length}</small>
          </h2>
        </header>
        {orderedModules.length ? (
          <ol className="dnd-list-modules">
            {orderedModules.map((module, index) => (
              <li key={module.id} className="dnd-list-module">
                <div className="dnd-list-module-head">
                  <span className="dnd-order-num">{index + 1}</span>
                  <button type="button" className="dnd-list-main" onClick={() => openInspector(nodeId.module(module.id), "main")}>
                    <strong title={module.title}>{module.title}</strong>
                    <small>{countLabel(module.lessonIds.length, WORDS.lesson)}</small>
                  </button>
                  <div className="dnd-list-actions">
                    <button type="button" className="dnd-icon-btn dnd-icon-btn--sm" onClick={() => moveModuleBy(module.id, -1)} disabled={index === 0 || orderPending} aria-label={`Модуль «${module.title}» выше`} title="Выше">
                      <Icon name="arrowUp" size={15} />
                    </button>
                    <button type="button" className="dnd-icon-btn dnd-icon-btn--sm" onClick={() => moveModuleBy(module.id, 1)} disabled={index === orderedModules.length - 1 || orderPending} aria-label={`Модуль «${module.title}» ниже`} title="Ниже">
                      <Icon name="arrowDown" size={15} />
                    </button>
                    <button type="button" className="dnd-icon-btn dnd-icon-btn--sm is-danger" onClick={() => requestDelete(nodeId.module(module.id))} aria-label={`Удалить модуль «${module.title}»`} title="Удалить">
                      <Icon name="trash" size={15} />
                    </button>
                  </div>
                </div>
                {module.lessonIds.length ? (
                  <ul className="dnd-list-rows">
                    {module.lessonIds.map((lessonId, lessonIndex) =>
                      lessonById.get(lessonId) ? (
                        <LessonRow key={lessonId} lesson={lessonById.get(lessonId)} index={lessonIndex} total={module.lessonIds.length} moduleId={module.id} />
                      ) : null,
                    )}
                  </ul>
                ) : (
                  <p className="dnd-muted">Пустой модуль — перенесите в него урок.</p>
                )}
              </li>
            ))}
          </ol>
        ) : (
          <p className="dnd-muted">Отметьте уроки без модуля и нажмите «Объединить в модуль».</p>
        )}
      </section>
    </div>
  );
}
