import { useEffect, useId, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useShallow } from "zustand/react/shallow";
import LessonContentEditor from "../components/LessonContentEditor";
import { createAgentConversationKey, useAgentStore } from "../stores/agentStore";
import { DIFFICULTY_OPTIONS, MATERIAL_STATUS } from "./constants";
import {
  countLabel,
  formatBytes,
  getLessonBlocks,
  MAX_CONTENT_BLOCKS,
  nodeId,
  parseNodeId,
  WORDS,
} from "./helpers";
import Icon, { Spinner } from "./icons";
import { getProgress, getStats } from "./selectors";
import { formFromEntity, hasFile, useDndCourseStore } from "./store";
import { SaveIndicator, StatusPill, useDndActions } from "./ui";

const TABS = {
  material: [
    { id: "content", label: "Контент" },
    { id: "ai", label: "ИИ-редактор" },
    { id: "props", label: "Свойства" },
  ],
  lesson: [
    { id: "main", label: "Основное" },
    { id: "content", label: "Контент" },
    { id: "goals", label: "Цели" },
    { id: "settings", label: "Настройки" },
  ],
  module: [
    { id: "main", label: "Основное" },
    { id: "lessons", label: "Уроки" },
  ],
  course: [
    { id: "main", label: "Карточка" },
    { id: "summary", label: "Сводка" },
  ],
};

const TYPE_META = {
  material: { icon: "file", label: "Материал" },
  lesson: { icon: "lesson", label: "Урок" },
  module: { icon: "module", label: "Модуль" },
  course: { icon: "course", label: "Курс" },
};

function Field({ label, error, hint, children, required = false }) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`dnd-field ${error ? "has-error" : ""}`}>
      <label htmlFor={id}>
        {label}
        {required ? <span aria-hidden="true"> *</span> : null}
      </label>
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined, "aria-required": required || undefined })}
      {hint ? (
        <small id={hintId} className="dnd-field-hint">
          {hint}
        </small>
      ) : null}
      {error ? (
        <small id={errorId} className="dnd-field-error" role="alert">
          {error}
        </small>
      ) : null}
    </div>
  );
}

function useEntityForm(key, type, entity) {
  const stored = useDndCourseStore((state) => state.forms[key]);
  const updateForm = useDndCourseStore((state) => state.updateForm);
  const values = stored || formFromEntity(type, entity);
  const change = (field) => (event) => updateForm(key, type, entity, { [field]: event.target.value });
  return { values, change, dirty: Boolean(stored) };
}

function SaveBar({ statusKey, onSave, onReset, dirty, disabled, label = "Сохранить" }) {
  const status = useDndCourseStore((state) => state.saveStatus[statusKey]);
  const error = useDndCourseStore((state) => state.saveErrors[statusKey]);
  const pending = useDndCourseStore((state) => Boolean(state.pending[statusKey]));
  return (
    <div className="dnd-savebar">
      {error ? (
        <p className="dnd-field-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="dnd-savebar-row">
        <SaveIndicator status={status} error={error} />
        <span className="dnd-node-actions-gap" />
        {dirty ? (
          <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={onReset} disabled={pending}>
            Отменить
          </button>
        ) : null}
        <button
          type="button"
          className="dnd-btn dnd-btn--solid dnd-btn--sm"
          onClick={onSave}
          disabled={disabled || pending || !dirty}
          aria-busy={pending}
        >
          {pending ? <Spinner size={13} /> : <Icon name="check" size={15} />}
          {pending ? "Сохраняем…" : label}
        </button>
      </div>
    </div>
  );
}

// ───────────── Материал ─────────────
function MaterialInspector({ material, tab }) {
  const course = useDndCourseStore((state) => state.course);
  const lesson = useDndCourseStore((state) =>
    material.lessonId ? state.lessons.find((item) => item.id === material.lessonId) : null,
  );
  const allLessons = useDndCourseStore((state) => state.lessons);
  const lessons = useMemo(
    () => allLessons.map((item) => ({ id: item.id, title: item.title, full: getLessonBlocks(item).length >= MAX_CONTENT_BLOCKS })),
    [allLessons],
  );
  const updateMarkdown = useDndCourseStore((state) => state.updateMaterialMarkdown);
  const askAi = useDndCourseStore((state) => state.askMaterialAi);
  const applyProposal = useDndCourseStore((state) => state.applyProposal);
  const rejectProposal = useDndCourseStore((state) => state.rejectProposal);
  const createLesson = useDndCourseStore((state) => state.createLessonFromMaterials);
  const addToLesson = useDndCourseStore((state) => state.addMaterialsToLesson);
  const retry = useDndCourseStore((state) => state.retryMaterial);
  const { pickFiles, requestDelete } = useDndActions();
  const [editing, setEditing] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [targetLesson, setTargetLesson] = useState("");
  const messagesRef = useRef(null);
  const conversationKey = createAgentConversationKey("editor", course?.id, `manual:${material.id}`);
  const conversation = useAgentStore((state) => state.conversations[conversationKey]);
  const aiBusy = conversation?.status === "loading";
  const aiError = material.aiError || conversation?.error || "";
  const messages = conversation?.messages || [];
  const lastUserMessage = [...messages].reverse().find((item) => item.role === "user");
  const isReady = material.status === "ready";

  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, aiBusy, material.proposal]);

  const send = () => {
    const text = prompt.trim();
    if (!text || aiBusy) return;
    setPrompt("");
    askAi(material.id, text);
  };

  if (tab === "ai") {
    return (
      <div className="dnd-ai">
        {!isReady ? <p className="dnd-muted">ИИ-редактор станет доступен, когда материал будет обработан.</p> : null}
        <div className="dnd-ai-messages nowheel" ref={messagesRef} aria-live="polite" aria-busy={aiBusy}>
          {messages.length === 0 ? (
            <div className="dnd-ai-msg is-assistant">
              Опишите, что поменять в материале. Я подготовлю правку — исходный текст не изменится, пока вы её не примените.
            </div>
          ) : null}
          {messages.map((message) => (
            <div key={message.id} className={`dnd-ai-msg is-${message.role}`}>
              {message.text}
            </div>
          ))}
          {aiBusy ? (
            <div className="dnd-ai-msg is-assistant is-thinking">
              <Spinner size={14} /> ИИ готовит правку…
            </div>
          ) : null}
        </div>
        {material.proposal ? (
          <section className="dnd-proposal" aria-label="Предложение ИИ">
            <header>
              <Icon name="sparkles" size={16} />
              <strong>Предложение ИИ</strong>
            </header>
            <div className="dnd-markdown dnd-markdown--compact nowheel">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{material.proposal}</ReactMarkdown>
            </div>
            <div className="dnd-proposal-actions">
              <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => rejectProposal(material.id)}>
                Не применять
              </button>
              <button type="button" className="dnd-btn dnd-btn--solid dnd-btn--sm" onClick={() => applyProposal(material.id)}>
                <Icon name="check" size={15} />
                Применить
              </button>
            </div>
          </section>
        ) : null}
        {aiError ? (
          <div className="dnd-inline-error" role="alert">
            <Icon name="alert" size={16} />
            <span>{aiError}</span>
            {lastUserMessage && !aiBusy ? (
              <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => askAi(material.id, lastUserMessage.text)}>
                <Icon name="retry" size={14} />
                Повторить
              </button>
            ) : null}
          </div>
        ) : null}
        <div className="dnd-ai-composer">
          <label className="dnd-visually-hidden" htmlFor={`ai-${material.id}`}>
            Запрос к ИИ-редактору
          </label>
          <textarea
            id={`ai-${material.id}`}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.nativeEvent.isComposing) return;
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send();
              }
            }}
            placeholder={aiBusy ? "Дождитесь ответа ИИ…" : "Например: сократи до тезисов и добавь пример"}
            maxLength={10000}
            disabled={!isReady}
            rows={3}
          />
          <button
            type="button"
            className="dnd-btn dnd-btn--solid dnd-btn--icon"
            onClick={send}
            disabled={!isReady || aiBusy || !prompt.trim()}
            aria-label="Отправить запрос ИИ"
            title="Отправить"
          >
            {aiBusy ? <Spinner size={14} /> : <Icon name="arrowUp" />}
          </button>
        </div>
      </div>
    );
  }

  if (tab === "props") {
    const status = material.lessonId ? "used" : material.status;
    return (
      <div className="dnd-stack">
        <dl className="dnd-props">
          <dt>Файл</dt>
          <dd title={material.fileName}>{material.fileName}</dd>
          <dt>Тип</dt>
          <dd>{material.fileKind}</dd>
          {material.size ? (
            <>
              <dt>Размер</dt>
              <dd>{formatBytes(material.size)}</dd>
            </>
          ) : null}
          <dt>Статус</dt>
          <dd>
            <StatusPill tone={MATERIAL_STATUS[status]?.tone} busy={material.status === "uploading"}>
              {MATERIAL_STATUS[status]?.label}
            </StatusPill>
          </dd>
          <dt>Урок</dt>
          <dd>{lesson ? lesson.title : "Не добавлен"}</dd>
        </dl>
        {material.status === "error" ? (
          <div className="dnd-inline-error" role="alert">
            <Icon name="alert" size={16} />
            <span>{material.error}</span>
            <button
              type="button"
              className="dnd-btn dnd-btn--ghost dnd-btn--sm"
              onClick={() => {
                if (material.tooBig || !hasFile(material.id) || !retry(material.id)) pickFiles({ replaceMaterialId: material.id });
              }}
            >
              <Icon name="retry" size={14} />
              {hasFile(material.id) && !material.tooBig ? "Повторить" : "Выбрать файл"}
            </button>
          </div>
        ) : null}
        {isReady && !material.lessonId ? (
          <div className="dnd-stack dnd-stack--tight">
            <button type="button" className="dnd-btn dnd-btn--solid dnd-btn--sm" onClick={() => createLesson([material.id])}>
              <Icon name="plus" size={15} />
              Создать урок из материала
            </button>
            {lessons.length ? (
              <div className="dnd-inline-form">
                <label className="dnd-visually-hidden" htmlFor={`to-lesson-${material.id}`}>
                  Добавить в существующий урок
                </label>
                <select id={`to-lesson-${material.id}`} value={targetLesson} onChange={(event) => setTargetLesson(event.target.value)}>
                  <option value="">Добавить в урок…</option>
                  {lessons.map((item) => (
                    <option key={item.id} value={item.id} disabled={item.full}>
                      {item.title}
                      {item.full ? ` (лимит ${MAX_CONTENT_BLOCKS})` : ""}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="dnd-btn dnd-btn--ghost dnd-btn--sm"
                  disabled={!targetLesson}
                  onClick={() => addToLesson(targetLesson, [material.id]).then((ok) => ok && setTargetLesson(""))}
                >
                  Добавить
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
        <button
          type="button"
          className="dnd-btn dnd-btn--danger-ghost dnd-btn--sm"
          onClick={() => requestDelete(nodeId.material(material.id))}
          disabled={Boolean(material.lessonId) || material.status === "uploading"}
          title={material.lessonId ? "Материал уже в уроке" : "Удалить материал"}
        >
          <Icon name="trash" size={15} />
          Удалить материал
        </button>
      </div>
    );
  }

  return (
    <div className="dnd-stack">
      {material.status === "uploading" ? (
        <p className="dnd-muted" role="status">
          <Spinner size={14} /> Обрабатываем документ…
        </p>
      ) : null}
      {material.status === "error" ? (
        <div className="dnd-inline-error" role="alert">
          <Icon name="alert" size={16} />
          <span>{material.error}</span>
        </div>
      ) : null}
      {isReady ? (
        <>
          <div className="dnd-segmented" role="group" aria-label="Режим просмотра">
            <button type="button" aria-pressed={!editing} className={!editing ? "is-on" : ""} onClick={() => setEditing(false)}>
              <Icon name="eye" size={15} /> Просмотр
            </button>
            <button type="button" aria-pressed={editing} className={editing ? "is-on" : ""} onClick={() => setEditing(true)}>
              <Icon name="edit" size={15} /> Markdown
            </button>
          </div>
          {material.lessonId ? (
            <p className="dnd-muted">
              <Icon name="info" size={14} /> Материал уже в уроке «{lesson?.title}». Правки здесь не меняют урок — редактируйте его контент в инспекторе урока.
            </p>
          ) : null}
          {editing ? (
            <>
              <label className="dnd-visually-hidden" htmlFor={`md-${material.id}`}>
                Markdown материала
              </label>
              <textarea
                id={`md-${material.id}`}
                className="dnd-md-editor nowheel"
                value={material.markdown}
                onChange={(event) => updateMarkdown(material.id, event.target.value)}
                spellCheck
              />
              <small className="dnd-field-hint">Изменения сохраняются в черновике автоматически.</small>
            </>
          ) : (
            <div className="dnd-markdown nowheel">
              {material.markdown.trim() ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{material.markdown}</ReactMarkdown>
              ) : (
                <p className="dnd-muted">Документ пустой.</p>
              )}
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

// ───────────── Урок ─────────────
function LessonInspector({ lesson, tab }) {
  const key = nodeId.lesson(lesson.id);
  const course = useDndCourseStore((state) => state.course);
  const { values, change, dirty } = useEntityForm(key, "lesson", lesson);
  const save = useDndCourseStore((state) => state.saveLessonMeta);
  const resetForm = useDndCourseStore((state) => state.resetForm);
  const setLessonContent = useDndCourseStore((state) => state.setLessonContent);
  const contentStatus = useDndCourseStore((state) => state.saveStatus[`${key}:content`]);
  const contentError = useDndCourseStore((state) => state.saveErrors[`${key}:content`]);
  const saveContentNow = useDndCourseStore((state) => state.saveLessonContentNow);
  const placement = useDndCourseStore(
    useShallow((state) => {
      const module = state.modules.find((item) => item.lessonIds.includes(lesson.id));
      return { moduleId: module?.id || "", index: module ? module.lessonIds.indexOf(lesson.id) : -1, total: module?.lessonIds.length || 0 };
    }),
  );
  const allModules = useDndCourseStore((state) => state.modules);
  const modules = useMemo(() => [...allModules].sort((a, b) => a.order - b.order), [allModules]);
  const materials = useDndCourseStore(useShallow((state) => state.materials.filter((item) => item.lessonId === lesson.id)));
  const moveToModule = useDndCourseStore((state) => state.moveLessonToModule);
  const moveBy = useDndCourseStore((state) => state.moveLessonBy);
  const openModuleDialog = useDndCourseStore((state) => state.openModuleDialog);
  const pending = useDndCourseStore((state) => Boolean(state.pending[key]));
  const { requestDelete } = useDndActions();
  const [moveTarget, setMoveTarget] = useState("");
  const titleError = dirty && !values.title.trim() ? "Укажите название урока" : "";
  const descriptionError = dirty && !values.description.trim() ? "Добавьте описание урока" : "";
  const saveBar = (
    <SaveBar
      statusKey={key}
      dirty={dirty}
      onSave={() => save(lesson.id)}
      onReset={() => resetForm(key)}
      disabled={Boolean(titleError || descriptionError)}
    />
  );

  if (tab === "content") {
    return (
      <div className="dnd-stack">
        <div className="dnd-savebar-row">
          <SaveIndicator status={contentStatus || "saved"} error={contentError} />
          <span className="dnd-node-actions-gap" />
          <small className="dnd-muted">
            {getLessonBlocks(lesson).length}/{MAX_CONTENT_BLOCKS} {WORDS.block[2]}
          </small>
        </div>
        {contentStatus === "error" ? (
          <div className="dnd-inline-error" role="alert">
            <Icon name="alert" size={16} />
            <span>{contentError}</span>
            <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => saveContentNow(lesson.id)}>
              <Icon name="retry" size={14} /> Повторить
            </button>
          </div>
        ) : null}
        <div className="dnd-lesson-editor nowheel">
          <LessonContentEditor
            courseId={course?.id}
            lesson={{ id: lesson.id, contentBlocks: getLessonBlocks(lesson), markdown: "" }}
            onChange={(changes) => setLessonContent(lesson.id, changes.contentBlocks || [])}
            contentLabel="Теория"
            blocksLabel="Блоки урока"
            showInsertControls={false}
          />
        </div>
      </div>
    );
  }

  if (tab === "goals") {
    return (
      <div className="dnd-stack">
        <Field label="Цели обучения" hint="Каждая цель с новой строки. Что студент сможет сделать после урока?">
          {(props) => (
            <textarea {...props} rows={8} value={values.learningObjectives} onChange={change("learningObjectives")} placeholder={"Объяснить, что такое…\nПрименить … на практике"} />
          )}
        </Field>
        {saveBar}
      </div>
    );
  }

  if (tab === "settings") {
    return (
      <div className="dnd-stack">
        <section className="dnd-subsection">
          <h4>Модуль</h4>
          <p className="dnd-muted">
            {placement.moduleId
              ? `Сейчас: «${modules.find((item) => item.id === placement.moduleId)?.title}», позиция ${placement.index + 1} из ${placement.total}.`
              : "Урок пока в черновике: на сервер он попадёт, когда вы добавите его в модуль."}
          </p>
          <div className="dnd-inline-form">
            <label className="dnd-visually-hidden" htmlFor={`move-${lesson.id}`}>
              Переместить в модуль
            </label>
            <select id={`move-${lesson.id}`} value={moveTarget} onChange={(event) => setMoveTarget(event.target.value)}>
              <option value="">Переместить в модуль…</option>
              {modules.map((item) => (
                <option key={item.id} value={item.id} disabled={item.id === placement.moduleId}>
                  {item.title}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="dnd-btn dnd-btn--ghost dnd-btn--sm"
              disabled={!moveTarget || pending}
              onClick={() => moveToModule(lesson.id, moveTarget).then(() => setMoveTarget(""))}
            >
              Переместить
            </button>
          </div>
          <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => openModuleDialog([lesson.id])}>
            <Icon name="plus" size={15} /> Новый модуль с этим уроком
          </button>
          {placement.moduleId ? (
            <div className="dnd-inline-form">
              <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => moveBy(lesson.id, -1)} disabled={placement.index <= 0 || pending}>
                <Icon name="arrowUp" size={15} /> Выше
              </button>
              <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => moveBy(lesson.id, 1)} disabled={placement.index >= placement.total - 1 || pending}>
                <Icon name="arrowDown" size={15} /> Ниже
              </button>
            </div>
          ) : null}
        </section>
        <section className="dnd-subsection">
          <h4>Материалы урока</h4>
          {materials.length ? (
            <ul className="dnd-mini-list">
              {materials.map((item) => (
                <li key={item.id}>
                  <Icon name="file" size={14} />
                  <span title={item.fileName}>{item.fileName}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="dnd-muted">Материалы не привязаны — контент добавлен вручную.</p>
          )}
        </section>
        <button type="button" className="dnd-btn dnd-btn--danger-ghost dnd-btn--sm" onClick={() => requestDelete(key)} disabled={pending}>
          <Icon name="trash" size={15} /> Удалить урок
        </button>
      </div>
    );
  }

  return (
    <div className="dnd-stack">
      <Field label="Название" required error={titleError}>
        {(props) => <input {...props} value={values.title} onChange={change("title")} maxLength={200} />}
      </Field>
      <Field label="Описание" required error={descriptionError}>
        {(props) => <textarea {...props} rows={4} value={values.description} onChange={change("description")} />}
      </Field>
      <Field label="Длительность, минут" hint="Сколько времени займёт урок">
        {(props) => (
          <input {...props} type="number" inputMode="numeric" min="1" max="600" value={values.estimatedTimeMinutes} onChange={change("estimatedTimeMinutes")} />
        )}
      </Field>
      {saveBar}
    </div>
  );
}

// ───────────── Модуль ─────────────
function ModuleInspector({ module, tab }) {
  const key = nodeId.module(module.id);
  const { values, change, dirty } = useEntityForm(key, "module", module);
  const save = useDndCourseStore((state) => state.saveModuleMeta);
  const resetForm = useDndCourseStore((state) => state.resetForm);
  const lessons = useDndCourseStore(
    useShallow((state) => module.lessonIds.map((id) => state.lessons.find((item) => item.id === id)).filter(Boolean)),
  );
  const position = useDndCourseStore(
    useShallow((state) => {
      const ordered = [...state.modules].sort((a, b) => a.order - b.order);
      return { index: ordered.findIndex((item) => item.id === module.id), total: ordered.length };
    }),
  );
  const orderPending = useDndCourseStore((state) => Boolean(state.pending["order:modules"] || state.pending[`order:${module.id}`]));
  const moveModuleBy = useDndCourseStore((state) => state.moveModuleBy);
  const moveLessonBy = useDndCourseStore((state) => state.moveLessonBy);
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const { requestDelete } = useDndActions();
  const titleError = dirty && !values.title.trim() ? "Укажите название модуля" : "";
  const descriptionError = dirty && !values.description.trim() ? "Добавьте описание модуля" : "";

  if (tab === "lessons") {
    return (
      <div className="dnd-stack">
        <p className="dnd-muted">
          Модуль {position.index + 1} из {position.total}. Порядок уроков меняется кнопками или перетаскиванием на холсте.
        </p>
        <div className="dnd-inline-form">
          <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => moveModuleBy(module.id, -1)} disabled={position.index <= 0 || orderPending}>
            <Icon name="arrowUp" size={15} /> Модуль выше
          </button>
          <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={() => moveModuleBy(module.id, 1)} disabled={position.index >= position.total - 1 || orderPending}>
            <Icon name="arrowDown" size={15} /> Модуль ниже
          </button>
        </div>
        {lessons.length ? (
          <ol className="dnd-order-list">
            {lessons.map((lesson, index) => (
              <li key={lesson.id}>
                <span className="dnd-order-num">{index + 1}</span>
                <button type="button" className="dnd-link" onClick={() => openInspector(nodeId.lesson(lesson.id), "main")} title={lesson.title}>
                  {lesson.title}
                </button>
                <button type="button" className="dnd-icon-btn dnd-icon-btn--sm" onClick={() => moveLessonBy(lesson.id, -1)} disabled={index === 0 || orderPending} aria-label={`Переместить «${lesson.title}» выше`} title="Выше">
                  <Icon name="arrowUp" size={14} />
                </button>
                <button type="button" className="dnd-icon-btn dnd-icon-btn--sm" onClick={() => moveLessonBy(lesson.id, 1)} disabled={index === lessons.length - 1 || orderPending} aria-label={`Переместить «${lesson.title}» ниже`} title="Ниже">
                  <Icon name="arrowDown" size={14} />
                </button>
              </li>
            ))}
          </ol>
        ) : (
          <p className="dnd-muted">В модуле пока нет уроков. Перетащите урок на модуль или используйте «Переместить в модуль» на карточке урока.</p>
        )}
        <button type="button" className="dnd-btn dnd-btn--danger-ghost dnd-btn--sm" onClick={() => requestDelete(key)}>
          <Icon name="trash" size={15} /> Удалить модуль
        </button>
      </div>
    );
  }

  return (
    <div className="dnd-stack">
      <Field label="Название" required error={titleError}>
        {(props) => <input {...props} value={values.title} onChange={change("title")} maxLength={200} />}
      </Field>
      <Field label="Описание" required error={descriptionError}>
        {(props) => <textarea {...props} rows={4} value={values.description} onChange={change("description")} />}
      </Field>
      <Field label="Цели обучения" hint="Каждая цель с новой строки">
        {(props) => <textarea {...props} rows={5} value={values.learningObjectives} onChange={change("learningObjectives")} />}
      </Field>
      <SaveBar statusKey={key} dirty={dirty} onSave={() => save(module.id)} onReset={() => resetForm(key)} disabled={Boolean(titleError || descriptionError)} />
    </div>
  );
}

// ───────────── Курс ─────────────
function CourseInspector({ course, tab }) {
  const { values, change, dirty } = useEntityForm("course", "course", course);
  const save = useDndCourseStore((state) => state.saveCourse);
  const resetForm = useDndCourseStore((state) => state.resetForm);
  const stats = useDndCourseStore(useShallow(getStats));
  const progress = useDndCourseStore((state) => getProgress(state).percent);
  const openFinish = useDndCourseStore((state) => state.openFinish);
  const titleError = dirty && !values.title.trim() ? "Укажите название курса" : "";
  const descriptionError = dirty && !values.description.trim() ? "Добавьте описание курса" : "";

  if (tab === "summary") {
    return (
      <div className="dnd-stack">
        <dl className="dnd-stats">
          <div><dt>Материалы</dt><dd>{stats.materials}</dd></div>
          <div><dt>Уроки</dt><dd>{stats.lessons}</dd></div>
          <div><dt>Модули</dt><dd>{stats.modules}</dd></div>
          <div className={stats.unassignedLessons ? "is-warn" : ""}><dt>Уроки без модуля</dt><dd>{stats.unassignedLessons}</dd></div>
        </dl>
        <div className="dnd-course-progress">
          <div className="dnd-course-progress-track"><i style={{ width: `${progress}%` }} /></div>
          <strong>{progress}%</strong>
        </div>
        <button type="button" className="dnd-btn dnd-btn--accent" onClick={openFinish}>
          <Icon name="flag" size={16} /> Итоговая проверка
        </button>
      </div>
    );
  }

  return (
    <div className="dnd-stack">
      <Field label="Название курса" required error={titleError}>
        {(props) => <input {...props} value={values.title} onChange={change("title")} maxLength={200} />}
      </Field>
      <Field label="Описание" required error={descriptionError}>
        {(props) => <textarea {...props} rows={4} value={values.description} onChange={change("description")} />}
      </Field>
      <Field label="Сложность">
        {(props) => (
          <select {...props} value={values.difficulty} onChange={change("difficulty")}>
            {DIFFICULTY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        )}
      </Field>
      <Field label="Теги" hint="Через запятую: python, backend, junior">
        {(props) => <input {...props} value={values.tags} onChange={change("tags")} />}
      </Field>
      <SaveBar statusKey="course" dirty={dirty} onSave={save} onReset={() => resetForm("course")} disabled={Boolean(titleError || descriptionError)} />
    </div>
  );
}

export default function Inspector({ variant = "side", resizeHandle = null }) {
  const activeNodeId = useDndCourseStore((state) => state.activeNodeId);
  const inspector = useDndCourseStore((state) => state.inspector);
  const setTab = useDndCourseStore((state) => state.setInspectorTab);
  const closeInspector = useDndCourseStore((state) => state.closeInspector);
  const { type, entityId } = parseNodeId(activeNodeId);
  const entity = useDndCourseStore((state) => {
    if (type === "course") return state.course;
    if (type === "material") return state.materials.find((item) => item.id === entityId);
    if (type === "lesson") return state.lessons.find((item) => item.id === entityId);
    if (type === "module") return state.modules.find((item) => item.id === entityId);
    return null;
  });
  const headingRef = useRef(null);

  useEffect(() => {
    if (inspector.open && variant === "sheet") headingRef.current?.focus();
  }, [activeNodeId, inspector.open, variant]);

  if (!inspector.open || !entity || !TABS[type]) return null;
  const tabs = TABS[type];
  const tab = tabs.some((item) => item.id === inspector.tab) ? inspector.tab : tabs[0].id;
  const meta = TYPE_META[type];
  const title = type === "material" ? entity.fileName : entity.title;

  return (
    <aside className={`dnd-inspector dnd-inspector--${variant}`} aria-label={`Инспектор: ${meta.label.toLowerCase()} «${title}»`}>
      {variant === "side" ? resizeHandle : null}
      <header className="dnd-inspector-head">
        <div className="dnd-inspector-kicker">
          <Icon name={meta.icon} size={16} />
          {meta.label}
        </div>
        <h2 tabIndex={-1} ref={headingRef} title={title}>
          {title}
        </h2>
        <button type="button" className="dnd-icon-btn" onClick={closeInspector} aria-label="Свернуть инспектор" title="Свернуть инспектор">
          <Icon name={variant === "sheet" ? "close" : "panelRight"} />
        </button>
      </header>
      <div className="dnd-tabs" role="tablist" aria-label="Разделы инспектора">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`dnd-tab-${item.id}`}
            aria-selected={tab === item.id}
            aria-controls="dnd-tabpanel"
            tabIndex={tab === item.id ? 0 : -1}
            className={tab === item.id ? "is-on" : ""}
            onClick={() => setTab(item.id)}
            onKeyDown={(event) => {
              const index = tabs.findIndex((t) => t.id === tab);
              if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                event.preventDefault();
                const next = tabs[(index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
                setTab(next.id);
                window.requestAnimationFrame(() => document.getElementById(`dnd-tab-${next.id}`)?.focus());
              }
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="dnd-inspector-body nowheel" role="tabpanel" id="dnd-tabpanel" aria-labelledby={`dnd-tab-${tab}`}>
        {type === "material" ? <MaterialInspector key={entity.id} material={entity} tab={tab} /> : null}
        {type === "lesson" ? <LessonInspector key={entity.id} lesson={entity} tab={tab} /> : null}
        {type === "module" ? <ModuleInspector key={entity.id} module={entity} tab={tab} /> : null}
        {type === "course" ? <CourseInspector course={entity} tab={tab} /> : null}
      </div>
    </aside>
  );
}

