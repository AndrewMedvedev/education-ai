import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { useShallow } from "zustand/react/shallow";
import { DIFFICULTY_LABEL, MATERIAL_STATUS, MODULE_LAYOUT } from "./constants";
import {
  countLabel,
  formatBytes,
  getLessonBlocks,
  getLessonFill,
  getModuleFill,
  markdownExcerpt,
  MAX_CONTENT_BLOCKS,
  nodeId,
  WORDS,
} from "./helpers";
import Icon, { Spinner } from "./icons";
import { moduleHeight } from "./layout";
import { getProgress, getStats, matchFilter, canFinish } from "./selectors";
import { useDndCourseStore } from "./store";
import { ActionMenu, StatusPill, useDndActions } from "./ui";

function useNodeChrome(id, type, entity) {
  return useDndCourseStore(
    useShallow((state) => {
      const hint = state.dropHint;
      return {
        dimmed: Boolean(state.filter) && !!entity && !matchFilter(state.filter, type, entity, state),
        highlighted: Boolean(state.filter) && !!entity && matchFilter(state.filter, type, entity, state),
        dropState:
          hint?.targetId === id ? (hint.valid ? "ok" : "bad") : null,
        active: state.activeNodeId === id && state.inspector.open,
        pending: Boolean(state.pending[id]),
      };
    }),
  );
}

function chromeClass({ dimmed, highlighted, dropState, active, pending }, selected) {
  return [
    selected ? "is-selected" : "",
    active ? "is-active" : "",
    dimmed ? "is-dimmed" : "",
    highlighted ? "is-highlighted" : "",
    dropState ? `is-drop-${dropState}` : "",
    pending ? "is-pending" : "",
  ]
    .filter(Boolean)
    .join(" ");
}

function FillBar({ value, label }) {
  return (
    <div className="dnd-fill" data-tip={`${label}: ${value}%`}>
      <span className="dnd-visually-hidden">
        {label}: {value}%
      </span>
      <i style={{ width: `${value}%` }} aria-hidden="true" />
    </div>
  );
}

function NodeButton({ icon, label, onClick, disabled, tone }) {
  return (
    <button
      type="button"
      className={`dnd-node-btn nodrag nopan ${tone ? `is-${tone}` : ""}`}
      onClick={(event) => {
        event.stopPropagation();
        onClick?.();
      }}
      disabled={disabled}
      aria-label={label}
      data-tip={label}
    >
      <Icon name={icon} size={20} />
    </button>
  );
}

// ───────────── Курс ─────────────
export const CourseNode = memo(function CourseNode({ id, selected }) {
  const course = useDndCourseStore((state) => state.course);
  const stats = useDndCourseStore(useShallow(getStats));
  const percent = useDndCourseStore((state) => getProgress(state).percent);
  const finishable = useDndCourseStore(canFinish);
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const openFinish = useDndCourseStore((state) => state.openFinish);
  const chrome = useNodeChrome(id, "course", course);
  if (!course) return null;

  return (
    <div
      className={`dnd-node dnd-node--course ${chromeClass(chrome, selected)}`}
      aria-label={`Курс «${course.title}». ${countLabel(stats.modules, WORDS.module)}, ${countLabel(stats.lessons, WORDS.lesson)}. Готовность ${percent}%.`}
    >
      <Handle type="target" position={Position.Left} className="dnd-handle" isConnectable={false} />
      <div className="dnd-node-kicker">
        <Icon name="course" size={16} />
        Курс
        <span className="dnd-node-kicker-end">{DIFFICULTY_LABEL[course.difficulty] || "—"}</span>
      </div>
      <h3 className="dnd-node-title" data-tip={course.title}>
        {course.title}
      </h3>
      <p className="dnd-node-meta">
        {countLabel(stats.modules, WORDS.module)} · {countLabel(stats.lessons, WORDS.lesson)}
      </p>
      <div className="dnd-course-progress" aria-hidden="true">
        <div className="dnd-course-progress-track">
          <i style={{ width: `${percent}%` }} />
        </div>
        <strong>{percent}%</strong>
      </div>
      <p className={`dnd-node-status ${finishable ? "is-ok" : ""}`}>
        <Icon name={finishable ? "check" : "info"} size={14} />
        {finishable ? "Структура готова к проверке" : "Структура ещё собирается"}
      </p>
      <div className="dnd-node-actions">
        <button
          type="button"
          className="dnd-btn dnd-btn--ghost dnd-btn--sm nodrag nopan"
          onClick={(event) => {
            event.stopPropagation();
            openInspector("course", "main");
          }}
        >
          <Icon name="settings" size={15} />
          Настройки
        </button>
        <button
          type="button"
          className="dnd-btn dnd-btn--accent dnd-btn--sm nodrag nopan"
          onClick={(event) => {
            event.stopPropagation();
            openFinish();
          }}
        >
          <Icon name="flag" size={15} />
          Проверить
        </button>
      </div>
    </div>
  );
});

// ───────────── Загрузка ─────────────
export const UploadNode = memo(function UploadNode() {
  const { pickFiles } = useDndActions();
  const isEmpty = useDndCourseStore((state) => state.materials.length === 0);
  return (
    <button
      type="button"
      className={`dnd-node dnd-node--upload nodrag ${isEmpty ? "is-calling" : ""}`}
      onClick={() => pickFiles()}
    >
      <Icon name="upload" size={22} />
      <span>
        <strong>Загрузить материалы</strong>
        <small>Перетащите файлы на холст или нажмите</small>
      </span>
    </button>
  );
});

// ───────────── Материал ─────────────
export const MaterialNode = memo(function MaterialNode({ id, data, selected }) {
  const material = useDndCourseStore((state) =>
    state.materials.find((item) => item.id === data.entityId),
  );
  const lessonTitle = useDndCourseStore((state) =>
    material?.lessonId
      ? state.lessons.find((lesson) => lesson.id === material.lessonId)?.title || "Урок"
      : null,
  );
  const selectedMaterialIds = useDndCourseStore(
    useShallow((state) =>
      state.selectedIds
        .filter((item) => item.startsWith("material:"))
        .map((item) => item.slice("material:".length)),
    ),
  );
  const chrome = useNodeChrome(id, "material", material);
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const createLesson = useDndCourseStore((state) => state.createLessonFromMaterials);
  const addToLesson = useDndCourseStore((state) => state.addMaterialsToLesson);
  const retry = useDndCourseStore((state) => state.retryMaterial);
  const { pickFiles, requestDelete } = useDndActions();
  if (!material) return null;

  const status = material.lessonId ? "used" : material.status;
  const statusInfo = MATERIAL_STATUS[status];
  const isReady = material.status === "ready" && !material.lessonId;
  const group =
    selected && selectedMaterialIds.length > 1 && selectedMaterialIds.includes(material.id)
      ? selectedMaterialIds
      : [material.id];

  const lessonItems = () => {
    const lessonOptions = useDndCourseStore.getState().lessons.map((lesson) => ({
      id: lesson.id,
      title: lesson.title,
      full: getLessonBlocks(lesson).length + group.length > MAX_CONTENT_BLOCKS,
    }));
    return [
    {
      key: "new",
      icon: "plus",
      label: group.length > 1 ? `Новый урок из ${group.length} материалов` : "Новый урок",
      onSelect: () => createLesson(group),
    },
    ...(lessonOptions.length ? [{ key: "sep", type: "separator" }, { key: "label", type: "label", label: "Существующий урок" }] : []),
    ...lessonOptions.map((lesson) => ({
      key: lesson.id,
      icon: "lesson",
      label: lesson.title,
      disabled: lesson.full,
      hint: lesson.full ? `Лимит ${MAX_CONTENT_BLOCKS} блоков` : undefined,
      onSelect: () => addToLesson(lesson.id, group),
    })),
    ];
  };

  return (
    <div
      className={`dnd-node dnd-node--material is-${status} ${chromeClass(chrome, selected)}`}
      aria-label={`Материал ${material.number}: ${material.fileName}. ${statusInfo?.label || ""}`}
      aria-busy={material.status === "uploading"}
    >
      <Handle type="source" position={Position.Right} className="dnd-handle" isConnectable={isReady} />
      <div className="dnd-node-kicker">
        <Icon name="file" size={15} />
        <span>#{material.number}</span>
        <span className="dnd-chip">{material.fileKind || "Файл"}</span>
        <span className="dnd-node-kicker-end">
          <StatusPill
            tone={statusInfo?.tone || "muted"}
            busy={material.status === "uploading"}
            icon={status === "error" ? "alert" : status === "used" ? "link" : status === "ready" ? "check" : null}
          >
            <span data-tip={statusInfo?.label}>{statusInfo?.short}</span>
          </StatusPill>
        </span>
      </div>
      <h3 className="dnd-node-title dnd-node-title--sm" data-tip={material.fileName}>
        {material.fileName}
      </h3>
      {material.status === "error" ? (
        <p className="dnd-node-error">{material.error || "Не удалось обработать документ."}</p>
      ) : material.status === "uploading" ? (
        <p className="dnd-node-excerpt">Загружаем файл и превращаем его в текст…</p>
      ) : (
        <p className="dnd-node-excerpt">
          {material.lessonId ? (
            <>
              <Icon name="link" size={13} /> В уроке «{lessonTitle}»
            </>
          ) : (
            markdownExcerpt(material.markdown, 110) || "Пустой документ"
          )}
        </p>
      )}
      <div className="dnd-node-actions dnd-node-toolbar" role="toolbar" aria-label="Действия с материалом">
        <NodeButton
          icon="eye"
          label="Открыть материал"
          onClick={() => openInspector(nodeId.material(material.id), "content")}
          disabled={material.status === "uploading"}
        />
        <NodeButton
          icon="sparkles"
          label="ИИ-редактор материала"
          onClick={() => openInspector(nodeId.material(material.id), "ai")}
          disabled={material.status !== "ready"}
        />
        {material.status === "error" ? (
          <NodeButton
            icon="retry"
            label="Повторить загрузку"
            onClick={() => {
              if (material.tooBig || !retry(material.id)) {
                pickFiles({ replaceMaterialId: material.id });
              }
            }}
          />
        ) : (
          <ActionMenu
            label="Добавить в урок"
            icon="lesson"
            items={lessonItems}
            disabled={!isReady}
            iconSize={20}
          />
        )}
        <span className="dnd-node-actions-gap" />
        {material.size ? <small className="dnd-node-size">{formatBytes(material.size)}</small> : null}
        <NodeButton
          icon="trash"
          tone="danger"
          label={material.lessonId ? "Материал уже в уроке — удалить нельзя" : "Удалить материал"}
          onClick={() => requestDelete(nodeId.material(material.id))}
          disabled={Boolean(material.lessonId) || material.status === "uploading"}
        />
      </div>
    </div>
  );
});

// ───────────── Урок ─────────────
export const LessonNode = memo(function LessonNode({ id, data, selected }) {
  const lesson = useDndCourseStore((state) =>
    state.lessons.find((item) => item.id === data.entityId),
  );
  const placement = useDndCourseStore(
    useShallow((state) => {
      const module = state.modules.find((item) => item.lessonIds.includes(data.entityId));
      return {
        moduleId: module?.id || null,
        moduleTitle: module?.title || null,
        index: module ? module.lessonIds.indexOf(data.entityId) : -1,
        total: module ? module.lessonIds.length : 0,
      };
    }),
  );
  const selectedLessonIds = useDndCourseStore(
    useShallow((state) =>
      state.selectedIds
        .filter((item) => item.startsWith("lesson:"))
        .map((item) => item.slice("lesson:".length)),
    ),
  );
  const chrome = useNodeChrome(id, "lesson", lesson);
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const moveLessonBy = useDndCourseStore((state) => state.moveLessonBy);
  const moveToModule = useDndCourseStore((state) => state.moveLessonToModule);
  const openModuleDialog = useDndCourseStore((state) => state.openModuleDialog);
  const contentStatus = useDndCourseStore(
    (state) => state.saveStatus[`${id}:content`],
  );
  const { requestDelete, previewLesson } = useDndActions();
  if (!lesson) return null;

  const blocks = getLessonBlocks(lesson).length;
  const fill = getLessonFill(lesson);
  const group =
    selected && selectedLessonIds.length > 1 && selectedLessonIds.includes(lesson.id)
      ? selectedLessonIds
      : [lesson.id];

  const moduleItems = () => {
    const moduleOptions = [...useDndCourseStore.getState().modules]
      .sort((a, b) => a.order - b.order)
      .map((module) => ({ id: module.id, title: module.title }));
    return [
    {
      key: "new",
      icon: "plus",
      label: group.length > 1 ? `Новый модуль из ${group.length} уроков` : "Новый модуль…",
      onSelect: () => openModuleDialog(group),
    },
    ...(moduleOptions.length ? [{ key: "sep", type: "separator" }, { key: "label", type: "label", label: "Существующий модуль" }] : []),
    ...moduleOptions.map((module) => ({
      key: module.id,
      icon: "module",
      label: module.title,
      disabled: module.id === placement.moduleId,
      hint: module.id === placement.moduleId ? "Урок уже здесь" : undefined,
      onSelect: () => moveToModule(lesson.id, module.id),
    })),
    ];
  };

  return (
    <div
      className={`dnd-node dnd-node--lesson ${placement.moduleId ? "is-nested" : "is-free"} ${chromeClass(chrome, selected)}`}
      aria-label={`Урок «${lesson.title}». ${placement.moduleTitle ? `Модуль «${placement.moduleTitle}», позиция ${placement.index + 1}` : "Без модуля"}. ${countLabel(blocks, WORDS.block)}.`}
    >
      <Handle type="target" position={Position.Left} className="dnd-handle" isConnectable />
      <Handle type="source" position={Position.Right} className="dnd-handle" isConnectable />
      <div className="dnd-node-kicker">
        <Icon name="lesson" size={15} />
        Урок
        {placement.moduleId ? (
          <span className="dnd-chip" data-tip={`Позиция в модуле: ${placement.index + 1}`}>
            №{placement.index + 1}
          </span>
        ) : null}
        <span className="dnd-node-kicker-end">
          {placement.moduleId ? null : (
            <span data-tip="Черновик: урок сохранится на сервере, когда вы добавите его в модуль">
              <StatusPill tone="warn" icon="alert">
                Черновик
              </StatusPill>
            </span>
          )}
          {contentStatus === "saving" ? <Spinner size={12} label="Сохраняем контент" /> : null}
        </span>
      </div>
      <h3 className="dnd-node-title dnd-node-title--sm" data-tip={lesson.title}>
        {lesson.title}
      </h3>
      <p className="dnd-node-meta">
        <span data-tip="Контентные блоки">
          {blocks}/{MAX_CONTENT_BLOCKS} {WORDS.block[2]}
        </span>
        <span>
          <Icon name="clock" size={13} />
          {lesson.estimatedTimeMinutes ? `${lesson.estimatedTimeMinutes} мин` : "—"}
        </span>
        {(lesson.materialIds || []).length ? (
          <span data-tip="Материалы, из которых собран урок">
            <Icon name="file" size={13} />
            {countLabel(lesson.materialIds.length, WORDS.material)}
          </span>
        ) : null}
      </p>
      <FillBar value={fill} label="Заполненность урока" />
      <div className="dnd-node-actions dnd-node-toolbar" role="toolbar" aria-label="Действия с уроком">
        <NodeButton
          icon="edit"
          label="Редактировать контент урока (с ИИ)"
          onClick={() => openInspector(id, "content")}
        />
        <NodeButton
          icon="settings"
          label="Название, описание и цели урока"
          onClick={() => openInspector(id, "main")}
        />
        <NodeButton
          icon="eye"
          label={lesson.isLocal ? "Урок ещё не на сервере — добавьте его в модуль, чтобы посмотреть" : "Посмотреть урок как студент"}
          onClick={() => previewLesson?.(lesson.id)}
          disabled={lesson.isLocal}
        />
        <ActionMenu label="Переместить в модуль" icon="module" items={moduleItems} iconSize={20} />
        {placement.moduleId ? (
          <>
            <NodeButton
              icon="arrowUp"
              label="Переместить выше"
              onClick={() => moveLessonBy(lesson.id, -1)}
              disabled={placement.index <= 0 || chrome.pending}
            />
            <NodeButton
              icon="arrowDown"
              label="Переместить ниже"
              onClick={() => moveLessonBy(lesson.id, 1)}
              disabled={placement.index >= placement.total - 1 || chrome.pending}
            />
          </>
        ) : null}
        <span className="dnd-node-actions-gap" />
        <NodeButton
          icon="trash"
          tone="danger"
          label="Удалить урок"
          onClick={() => requestDelete(id)}
          disabled={chrome.pending}
        />
      </div>
    </div>
  );
});

// ───────────── Модуль ─────────────
export const ModuleNode = memo(function ModuleNode({ id, data, selected }) {
  const module = useDndCourseStore((state) =>
    state.modules.find((item) => item.id === data.entityId),
  );
  const position = useDndCourseStore(
    useShallow((state) => {
      const ordered = [...state.modules].sort((a, b) => a.order - b.order);
      return {
        index: ordered.findIndex((item) => item.id === data.entityId),
        total: ordered.length,
      };
    }),
  );
  const chrome = useNodeChrome(id, "module", module);
  const orderPending = useDndCourseStore(
    (state) => Boolean(state.pending["order:modules"] || state.pending[`order:${data.entityId}`]),
  );
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const moveModuleBy = useDndCourseStore((state) => state.moveModuleBy);
  const { requestDelete } = useDndActions();
  if (!module) return null;

  const lessons = module.lessonIds.length;
  return (
    <div
      className={`dnd-node dnd-node--module ${chromeClass(chrome, selected)}`}
      style={{ width: MODULE_LAYOUT.width, height: moduleHeight(lessons) }}
      aria-label={`Модуль ${position.index + 1}: «${module.title}». ${countLabel(lessons, WORDS.lesson)}.`}
    >
      <Handle type="target" position={Position.Left} className="dnd-handle" isConnectable />
      <Handle type="source" position={Position.Right} className="dnd-handle" isConnectable={false} />
      <header className="dnd-module-head">
        <div className="dnd-node-kicker">
          <Icon name="module" size={15} />
          Модуль {position.index + 1}
          <span className="dnd-node-kicker-end">
            {orderPending ? <Spinner size={12} label="Сохраняем порядок" /> : null}
            {countLabel(lessons, WORDS.lesson)}
          </span>
        </div>
        <h3 className="dnd-node-title dnd-node-title--sm" data-tip={module.title}>
          {module.title}
        </h3>
        <div className="dnd-module-toolbar">
          <FillBar value={getModuleFill(module)} label="Заполненность модуля" />
          <span className="dnd-module-buttons">
          <NodeButton icon="edit" label="Редактировать модуль" onClick={() => openInspector(id, "main")} />
          <NodeButton
            icon="arrowUp"
            label="Модуль выше"
            onClick={() => moveModuleBy(module.id, -1)}
            disabled={position.index <= 0 || orderPending}
          />
          <NodeButton
            icon="arrowDown"
            label="Модуль ниже"
            onClick={() => moveModuleBy(module.id, 1)}
            disabled={position.index >= position.total - 1 || orderPending}
          />
          <NodeButton
            icon="trash"
            tone="danger"
            label="Удалить модуль"
            onClick={() => requestDelete(id)}
            disabled={chrome.pending}
          />
          </span>
        </div>
      </header>
      <footer className={`dnd-module-drop ${lessons ? "" : "is-empty"}`}>
        <Icon name="plus" size={14} />
        {lessons ? "Перетащите сюда ещё урок" : "Перетащите урок в модуль"}
      </footer>
    </div>
  );
});

export const nodeTypes = {
  course: CourseNode,
  upload: UploadNode,
  material: MaterialNode,
  lesson: LessonNode,
  module: ModuleNode,
};
