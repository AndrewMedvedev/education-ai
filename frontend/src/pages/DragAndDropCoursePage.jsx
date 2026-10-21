import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Canvas from "../dnd-course/Canvas";
import { FinishDialog, MaterialPickerDialog, ModuleDialog } from "../dnd-course/Dialogs";
import { Celebration, Onboarding } from "../dnd-course/Extras";
import { countLabel, parseNodeId, WORDS } from "../dnd-course/helpers";
import Inspector from "../dnd-course/Inspector";
import ListView from "../dnd-course/ListView";
import Palette from "../dnd-course/Palette";
import StartScreen from "../dnd-course/StartScreen";
import { useDndCourseStore } from "../dnd-course/store";
import TopBar from "../dnd-course/TopBar";
import DndTooltipLayer from "../dnd-course/Tooltip";
import { ConfirmDialog, DndActionsContext, LiveRegion, Toasts } from "../dnd-course/ui";
import "../styles/dnd-course.css";

function useMedia(query) {
  const get = () => typeof window !== "undefined" && window.matchMedia(query).matches;
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    const media = window.matchMedia(query);
    const onChange = () => setMatches(media.matches);
    media.addEventListener("change", onChange);
    onChange();
    return () => media.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

export default function DragAndDropCoursePage() {
  const navigate = useNavigate();
  const openPreview = useCallback(
    async ({ courseId }) => navigate(`/drag-and-drop-course/${courseId}/preview`),
    [navigate],
  );
  const hydrate = useDndCourseStore((state) => state.hydrate);
  const hydrated = useDndCourseStore((state) => state.hydrated);
  const hasCourse = useDndCourseStore((state) => Boolean(state.course?.id));
  const paletteOpen = useDndCourseStore((state) => state.paletteOpen);
  const inspectorOpen = useDndCourseStore((state) => state.inspector.open && Boolean(state.activeNodeId));
  const inspectorWide = useDndCourseStore(
    (state) => state.inspector.open && state.inspector.tab === "content" && String(state.activeNodeId || "").startsWith("lesson:"),
  );
  const viewMode = useDndCourseStore((state) => state.viewMode);
  const setPaletteOpen = useDndCourseStore((state) => state.setPaletteOpen);
  const closeInspector = useDndCourseStore((state) => state.closeInspector);
  const isMobile = useMedia("(max-width: 767px)");
  const isCompact = useMedia("(max-width: 1279px)");
  const fileInputRef = useRef(null);
  const workspaceRef = useRef(null);
  const inspectorWidths = useDndCourseStore((state) => state.inspectorWidths);
  const setInspectorWidth = useDndCourseStore((state) => state.setInspectorWidth);
  const fullscreen = useDndCourseStore((state) => state.fullscreen);
  const toggleFullscreen = useDndCourseStore((state) => state.toggleFullscreen);
  const courseIdForPreview = useDndCourseStore((state) => state.course?.id);
  const pickOptionsRef = useRef({});
  const rootRef = useRef(null);
  const [top, setTop] = useState(160);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isCompact) setPaletteOpen(false);
  }, [isCompact, setPaletteOpen]);

  useLayoutEffect(() => {
    const measure = () => {
      const rect = rootRef.current?.getBoundingClientRect();
      if (rect) setTop(Math.max(0, Math.round(rect.top + window.scrollY)));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [hasCourse]);

  const pickFiles = useCallback((options = {}) => {
    pickOptionsRef.current = options;
    const input = fileInputRef.current;
    if (!input) return;
    input.multiple = !options.replaceMaterialId;
    input.click();
  }, []);

  const requestDelete = useCallback((id) => {
    const state = useDndCourseStore.getState();
    const { type, entityId } = parseNodeId(id);
    if (type === "material") {
      const material = state.materials.find((item) => item.id === entityId);
      if (!material || material.lessonId) return;
      state.openConfirm({
        title: `Удалить материал «${material.fileName}»?`,
        message: "Материал исчезнет с холста.",
        consequences: [
          "Распознанный текст документа будет потерян — файл придётся загрузить заново.",
          "На сервере материал не хранится, поэтому больше ничего не изменится.",
        ],
        onConfirm: () => state.deleteMaterial(entityId),
      });
    }
    if (type === "lesson") {
      const lesson = state.lessons.find((item) => item.id === entityId);
      if (!lesson) return;
      const module = state.modules.find((item) => item.lessonIds.includes(entityId));
      state.openConfirm({
        title: `Удалить урок «${lesson.title}»?`,
        message: "Урок будет удалён на сервере вместе с контентом. Отменить это нельзя.",
        consequences: [
          "Материалы урока снова станут свободными и останутся на холсте.",
          ...(module && module.lessonIds.length === 1 ? [`Модуль «${module.title}» станет пустым — сам модуль не удалится.`] : []),
        ],
        onConfirm: () => useDndCourseStore.getState().deleteLesson(entityId),
      });
    }
    if (type === "module") {
      const module = state.modules.find((item) => item.id === entityId);
      if (!module) return;
      state.openConfirm({
        title: `Удалить модуль «${module.title}»?`,
        message: "Модуль будет удалён на сервере. Отменить это нельзя.",
        consequences: module.lessonIds.length
          ? [
              `Вместе с модулем сервер удалит ${countLabel(module.lessonIds.length, WORDS.lesson)} внутри него.`,
              "Материалы этих уроков вернутся на холст как свободные.",
            ]
          : ["Модуль пустой — уроки не затронуты."],
        onConfirm: () => useDndCourseStore.getState().deleteModule(entityId),
      });
    }
  }, []);

  const previewLesson = useCallback(
    (lessonId) => {
      if (!courseIdForPreview) return;
      navigate(`/drag-and-drop-course/${courseIdForPreview}/preview?lesson=${encodeURIComponent(lessonId)}`);
    },
    [courseIdForPreview, navigate],
  );
  const actions = useMemo(
    () => ({ pickFiles, requestDelete, previewLesson }),
    [pickFiles, requestDelete, previewLesson],
  );

  useEffect(() => {
    if (!fullscreen) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape" && !document.querySelector(".dnd-modal")) toggleFullscreen();
    };
    document.body.classList.add("is-dnd-fullscreen");
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.classList.remove("is-dnd-fullscreen");
      window.removeEventListener("keydown", onKey);
    };
  }, [fullscreen, toggleFullscreen]);

  const widthKind = inspectorWide ? "wide" : "normal";
  const inspectorWidth = (inspectorWidths || {})[widthKind] || (inspectorWide ? 660 : 440);
  const clampWidth = (value) => {
    const total = workspaceRef.current?.getBoundingClientRect().width || window.innerWidth;
    return Math.max(340, Math.min(value, Math.min(980, total - 380)));
  };
  const startResize = (event) => {
    event.preventDefault();
    const workspace = workspaceRef.current;
    if (!workspace) return;
    const right = workspace.getBoundingClientRect().right;
    let next = inspectorWidth;
    const move = (moveEvent) => {
      next = clampWidth(right - moveEvent.clientX);
      workspace.style.setProperty("--dnd-inspector-w", `${next}px`);
    };
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      document.body.classList.remove("is-dnd-resizing");
      setInspectorWidth(widthKind, next);
    };
    document.body.classList.add("is-dnd-resizing");
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };
  const resizeHandle = (
    <div
      className="dnd-inspector-resizer"
      role="separator"
      aria-orientation="vertical"
      aria-label="Ширина правой панели"
      aria-valuenow={inspectorWidth}
      aria-valuemin={340}
      aria-valuemax={980}
      tabIndex={0}
      title="Потяните, чтобы изменить ширину. Двойной клик — вернуть по умолчанию"
      onPointerDown={startResize}
      onDoubleClick={() => setInspectorWidth(widthKind, inspectorWide ? 660 : 440)}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
          event.preventDefault();
          setInspectorWidth(widthKind, clampWidth(inspectorWidth + (event.key === "ArrowLeft" ? 40 : -40)));
        }
      }}
    />
  );
  const mode = viewMode || (isMobile ? "list" : "canvas");
  const paletteVariant = isCompact ? "sheet" : "side";
  const inspectorVariant = isMobile ? "sheet" : isCompact ? "drawer" : "side";

  if (!hydrated) return null;

  return (
    <DndActionsContext.Provider value={actions}>
      <section
        ref={rootRef}
        className={`dnd-builder ${hasCourse ? "has-course" : "is-start"} is-mode-${mode} ${isCompact ? "is-compact" : ""} ${isMobile ? "is-mobile" : ""} ${fullscreen && hasCourse ? "is-fullscreen" : ""}`}
        style={{ "--dnd-top": `${top}px` }}
      >
        {hasCourse ? (
          <>
            <TopBar isMobile={isMobile} onPreview={openPreview} />
            <div
              ref={workspaceRef}
              style={{ "--dnd-inspector-w": `${inspectorWidth}px` }}
              className={`dnd-workspace ${paletteOpen && paletteVariant === "side" && mode === "canvas" ? "has-palette" : ""} ${inspectorOpen && inspectorVariant === "side" ? "has-inspector" : ""} ${inspectorWide ? "has-wide-inspector" : ""}`}>
              {mode === "canvas" && paletteOpen ? (
                <>
                  {paletteVariant === "sheet" ? (
                    <button type="button" className="dnd-scrim" aria-label="Закрыть палитру" onClick={() => setPaletteOpen(false)} />
                  ) : null}
                  <Palette variant={paletteVariant} />
                </>
              ) : null}
              <main className="dnd-main">
                {mode === "canvas" ? (
                  <>
                    <Canvas />
                    <Onboarding />
                  </>
                ) : (
                  <ListView />
                )}
              </main>
              {inspectorOpen ? (
                <>
                  {inspectorVariant !== "side" ? (
                    <button type="button" className="dnd-scrim" aria-label="Закрыть инспектор" onClick={closeInspector} />
                  ) : null}
                  <Inspector variant={inspectorVariant} resizeHandle={resizeHandle} />
                </>
              ) : null}
            </div>
          </>
        ) : (
          <StartScreen />
        )}

        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="dnd-visually-hidden"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(event) => {
            const files = Array.from(event.target.files || []);
            const options = pickOptionsRef.current || {};
            const store = useDndCourseStore.getState();
            if (files.length) {
              if (options.replaceMaterialId) store.retryMaterial(options.replaceMaterialId, files[0]);
              else store.addFiles(files, { position: options.position || null, attachToLessonId: options.attachToLessonId || null });
            }
            pickOptionsRef.current = {};
            event.target.value = "";
          }}
        />

        <ModuleDialog />
        <MaterialPickerDialog />
        <FinishDialog onCreateCourse={openPreview} />
        <ConfirmDialog />
        <Toasts />
        <LiveRegion />
        <DndTooltipLayer />
        <Celebration />
      </section>
    </DndActionsContext.Provider>
  );
}

