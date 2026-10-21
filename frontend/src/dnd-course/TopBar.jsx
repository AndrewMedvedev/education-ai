import { useNavigate } from "react-router-dom";
import { useShallow } from "zustand/react/shallow";
import Icon, { Spinner } from "./icons";
import { canFinish, getGlobalSaveState, getNextTask, getProgress } from "./selectors";
import { useDndCourseStore } from "./store";
import { ActionMenu } from "./ui";

const SAVE_TEXT = {
  saving: "Сохраняем…",
  error: "Есть ошибки сохранения",
  dirty: "Есть несохранённые изменения",
  saved: "Все изменения сохранены",
};

export default function TopBar({ isMobile, onPreview }) {
  const navigate = useNavigate();
  const course = useDndCourseStore((state) => state.course);
  const progress = useDndCourseStore(
    useShallow((state) => {
      const value = getProgress(state);
      return { percent: value.percent, currentStep: value.currentStep, doneCount: value.doneCount };
    }),
  );
  const nextTask = useDndCourseStore(getNextTask);
  const saveState = useDndCourseStore(getGlobalSaveState);
  const finishable = useDndCourseStore(canFinish);
  const finishing = useDndCourseStore((state) => Boolean(state.pending.finish));
  const paletteOpen = useDndCourseStore((state) => state.paletteOpen);
  const inspectorOpen = useDndCourseStore((state) => state.inspector.open && Boolean(state.activeNodeId));
  const viewMode = useDndCourseStore((state) => state.viewMode);
  const setPaletteOpen = useDndCourseStore((state) => state.setPaletteOpen);
  const setViewMode = useDndCourseStore((state) => state.setViewMode);
  const openInspector = useDndCourseStore((state) => state.openInspector);
  const openFinish = useDndCourseStore((state) => state.openFinish);
  const openConfirm = useDndCourseStore((state) => state.openConfirm);
  const resetAll = useDndCourseStore((state) => state.resetAll);
  const restartOnboarding = useDndCourseStore((state) => state.restartOnboarding);
  const activeNodeId = useDndCourseStore((state) => state.activeNodeId);
  const fullscreen = useDndCourseStore((state) => state.fullscreen);
  const toggleFullscreen = useDndCourseStore((state) => state.toggleFullscreen);
  const effectiveMode = viewMode || (isMobile ? "list" : "canvas");
  const stepText = progress.doneCount >= 4 ? "Все шаги пройдены" : `Шаг ${progress.currentStep} из 4`;

  const menuItems = [
    ...(isMobile
      ? [{ key: "settings", icon: "settings", label: "Настройки курса", onSelect: () => openInspector("course", "main") }]
      : []),
    {
      key: "mode",
      icon: effectiveMode === "canvas" ? "list" : "canvas",
      label: effectiveMode === "canvas" ? "Режим списка" : "Режим холста",
      onSelect: () => setViewMode(effectiveMode === "canvas" ? "list" : "canvas"),
    },
    ...(isMobile && course?.id
      ? [{ key: "preview", icon: "eye", label: "Просмотр курса", onSelect: () => onPreview?.({ courseId: course.id }) }]
      : []),
    { key: "help", icon: "help", label: "Показать обучение", onSelect: restartOnboarding },
    { key: "sep", type: "separator" },
    {
      key: "reset",
      icon: "restart",
      label: "Начать заново",
      danger: true,
      onSelect: () =>
        openConfirm({
          title: "Начать заново?",
          message: "Черновик конструктора будет очищен: материалы, раскладка и несохранённые формы пропадут.",
          consequences: [
            "Уже созданный курс, уроки и модули на сервере не удаляются.",
            "Загруженные документы придётся добавить повторно.",
          ],
          confirmLabel: "Очистить черновик",
          onConfirm: () => resetAll(),
        }),
    },
  ];

  return (
    <header className="dnd-topbar">
      <div className="dnd-topbar-left">
        <button
          type="button"
          className="dnd-icon-btn"
          onClick={() => (window.history.length > 1 ? navigate(-1) : navigate("/"))}
          aria-label="Вернуться назад"
          title="Назад"
        >
          <Icon name="arrowLeft" />
        </button>
        {effectiveMode === "canvas" ? (
          <button
            type="button"
            className={`dnd-icon-btn dnd-topbar-palette ${paletteOpen ? "is-on" : ""}`}
            onClick={() => setPaletteOpen(!paletteOpen)}
            aria-pressed={paletteOpen}
            aria-label={paletteOpen ? "Скрыть палитру" : "Показать палитру"}
            title="Палитра"
          >
            <Icon name="panel" />
          </button>
        ) : null}
        <div className="dnd-topbar-title">
          <h1>Drag &amp; Drop курс</h1>
          <span title={course?.title}>{course?.title}</span>
        </div>
      </div>

      <div className="dnd-topbar-center">
        <div
          className="dnd-progress"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress.percent}
          aria-valuetext={`${progress.percent}%. ${stepText}. ${nextTask}`}
          aria-label="Прогресс создания курса"
        >
          {[0, 1, 2, 3].map((index) => (
            <i key={index} className={index < progress.doneCount ? "is-done" : index === progress.doneCount ? "is-current" : ""} />
          ))}
        </div>
        <p className="dnd-topbar-task">
          <strong>{stepText}</strong>
          <span aria-hidden="true"> · </span>
          <span>{nextTask}</span>
        </p>
        <span className={`dnd-topbar-save is-${saveState}`} role="status" title={SAVE_TEXT[saveState]}>
          {saveState === "saving" ? <Spinner size={12} /> : <Icon name={saveState === "saved" ? "check" : saveState === "error" ? "alert" : "edit"} size={13} />}
          <span className="dnd-topbar-save-text">{SAVE_TEXT[saveState]}</span>
        </span>
      </div>

      <div className="dnd-topbar-right">
        {isMobile ? (
          <div className="dnd-segmented dnd-segmented--sm" role="group" aria-label="Режим отображения">
            <button type="button" aria-pressed={effectiveMode === "canvas"} className={effectiveMode === "canvas" ? "is-on" : ""} onClick={() => setViewMode("canvas")}>
              <Icon name="canvas" size={15} /> Холст
            </button>
            <button type="button" aria-pressed={effectiveMode === "list"} className={effectiveMode === "list" ? "is-on" : ""} onClick={() => setViewMode("list")}>
              <Icon name="list" size={15} /> Список
            </button>
          </div>
        ) : null}
        {!isMobile ? (
          <button type="button" className="dnd-btn dnd-btn--ghost dnd-topbar-settings" onClick={() => openInspector("course", "main")} aria-label="Настройки курса" title="Настройки курса">
            <Icon name="settings" size={16} />
            <span>Настройки курса</span>
          </button>
        ) : null}
        {!isMobile && !inspectorOpen && activeNodeId && effectiveMode === "canvas" ? (
          <button type="button" className="dnd-icon-btn" onClick={() => openInspector(activeNodeId)} aria-label="Показать инспектор" title="Показать инспектор">
            <Icon name="panelRight" />
          </button>
        ) : null}
        {!isMobile && course?.id ? (
          <button
            type="button"
            className="dnd-btn dnd-btn--ghost dnd-topbar-settings"
            onClick={() => onPreview?.({ courseId: course.id })}
            title="Посмотреть, как курс выглядит для студента"
            aria-label="Просмотр курса"
          >
            <Icon name="eye" size={16} />
            <span>Просмотр курса</span>
          </button>
        ) : null}
        <button
          type="button"
          className="dnd-btn dnd-btn--accent"
          onClick={openFinish}
          disabled={!finishable || finishing}
          aria-busy={finishing}
          title={finishable ? "Проверить структуру и посмотреть курс" : "Нужен хотя бы один модуль с уроком и завершённые операции"}
        >
          {finishing ? <Spinner size={14} /> : <Icon name="flag" size={16} />}
          {finishing ? "Открываем курс…" : "Завершить"}
        </button>
        {!isMobile ? (
          <button
            type="button"
            className={`dnd-icon-btn ${fullscreen ? "is-on" : ""}`}
            onClick={toggleFullscreen}
            aria-pressed={fullscreen}
            aria-label={fullscreen ? "Выйти из полноэкранного режима (Esc)" : "Развернуть конструктор на весь экран"}
            title={fullscreen ? "Свернуть (Esc)" : "На весь экран"}
          >
            <Icon name={fullscreen ? "minimize" : "maximize"} />
          </button>
        ) : null}
        <ActionMenu label="Дополнительные действия" items={menuItems} buttonClassName="dnd-icon-btn" align="end" />
      </div>
    </header>
  );
}
