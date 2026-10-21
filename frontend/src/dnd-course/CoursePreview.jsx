import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import CourseNavigationTree from "../components/CourseNavigationTree";
import SectionTop from "../components/SectionTop";
import ContentBlocks from "../components/course/ContentBlocks";
import CourseBasicInfo from "../components/course/CourseBasicInfo";
import LessonBasicInfo from "../components/course/LessonBasicInfo";
import LessonList from "../components/course/LessonList";
import ModuleBasicInfo from "../components/course/ModuleBasicInfo";
import ModuleList from "../components/course/ModuleList";
import "../components/course/course-viewer.css";
import { useSessionStore } from "../stores/sessionStore";
import { archiveCourse, publishCourse, setCourseInviteOnly } from "../utils/api";
import { getApiErrorMessage } from "./helpers";
import Icon, { Spinner } from "./icons";
import { fetchCourseStructure, fetchLessonBlocks } from "./serverCourse";
import { useDndCourseStore } from "./store";
import { ActionMenu, ConfirmDialog, StatusPill, Toasts } from "./ui";
import DndTooltipLayer from "./Tooltip";

const STATUS = {
  draft: { label: "Черновик", tone: "muted" },
  in_generation: { label: "Черновик", tone: "muted" },
  published: { label: "Опубликован", tone: "ok" },
  invite_only: { label: "Только по приглашению", tone: "used" },
  archived: { label: "В архиве", tone: "error" },
};

export default function CoursePreview({ courseId }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedLessonId = searchParams.get("lesson");
  const user = useSessionStore((state) => state.user);
  const hydrate = useDndCourseStore((state) => state.hydrate);
  const toast = useDndCourseStore((state) => state.toast);
  const openConfirm = useDndCourseStore((state) => state.openConfirm);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(null);
  const [action, setAction] = useState("");
  const [activeLessonId, setActiveLessonId] = useState(null);
  const [activeModuleId, setActiveModuleId] = useState(null);
  const [lessonBlocks, setLessonBlocks] = useState({});
  const [lessonError, setLessonError] = useState("");

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const load = useCallback(async () => {
    setError("");
    setData(null);
    try {
      const result = await fetchCourseStructure(courseId);
      setData(result);
      setStatus(result.status);
      const requested = requestedLessonId && result.modules.some((module) => module.lessons.some((lesson) => lesson.id === requestedLessonId));
      setActiveLessonId((current) => current || (requested ? requestedLessonId : null));
    } catch (loadError) {
      setError(getApiErrorMessage(loadError, "Не удалось загрузить курс."));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!activeLessonId || lessonBlocks[activeLessonId]) return;
    let cancelled = false;
    setLessonError("");
    fetchLessonBlocks(activeLessonId)
      .then((blocks) => {
        if (!cancelled) setLessonBlocks((current) => ({ ...current, [activeLessonId]: blocks }));
      })
      .catch((loadError) => {
        if (!cancelled) setLessonError(getApiErrorMessage(loadError, "Не удалось загрузить урок."));
      });
    return () => {
      cancelled = true;
    };
  }, [activeLessonId, lessonBlocks]);

  const flatLessons = useMemo(
    () =>
      (data?.modules || []).flatMap((module, moduleIndex) =>
        module.lessons.map((lesson, lessonIndex) => ({ ...lesson, module, moduleIndex, lessonIndex })),
      ),
    [data],
  );
  const activeIndex = flatLessons.findIndex((lesson) => lesson.id === activeLessonId);
  const active = activeIndex >= 0 ? flatLessons[activeIndex] : null;
  const treeCourse = useMemo(
    () =>
      data
        ? {
            ...data.course,
            blocks: data.modules.map((module) => ({ ...module, practice: [] })),
          }
        : null,
    [data],
  );
  const moduleIndex = (data?.modules || []).findIndex((module) => module.id === (active?.module.id || activeModuleId));
  const activeModule = moduleIndex >= 0 ? { ...data.modules[moduleIndex], order: moduleIndex } : null;
  const openBlock = (blockId) => {
    setActiveModuleId(blockId);
    setActiveLessonId(null);
  };
  const openLesson = (lessonId) => {
    const lesson = flatLessons.find((item) => item.id === lessonId);
    if (lesson) setActiveModuleId(lesson.module.id);
    setActiveLessonId(lessonId);
  };
  const openOverview = () => {
    setActiveModuleId(null);
    setActiveLessonId(null);
  };

  const backToBuilder = async () => {
    if (action) return;
    const store = useDndCourseStore.getState();
    if (store.course?.id === courseId) {
      navigate("/drag-and-drop-course");
      return;
    }
    setAction("builder");
    try {
      await store.loadFromServer(courseId);
      navigate("/drag-and-drop-course");
    } catch (loadError) {
      toast("error", getApiErrorMessage(loadError, "Не удалось открыть курс на холсте."));
      setAction("");
    }
  };

  const changeStatus = async (next) => {
    if (action) return;
    setAction(next);
    try {
      const result = next === "publish" ? await publishCourse(courseId) : await setCourseInviteOnly(courseId);
      setStatus(result?.status || (next === "publish" ? "published" : "invite_only"));
      toast("success", next === "publish" ? "Курс опубликован" : "Курс доступен только по приглашению");
    } catch (changeError) {
      toast("error", getApiErrorMessage(changeError, "Не удалось изменить статус курса."));
    } finally {
      setAction("");
    }
  };

  const removeCourse = () =>
    openConfirm({
      title: `Удалить курс «${data?.course?.title || ""}»?`,
      message: "Курс уйдёт в архив и пропадёт из каталога.",
      consequences: ["Студенты больше не смогут его открыть.", "Черновик конструктора для этого курса будет очищен."],
      confirmLabel: "Удалить курс",
      onConfirm: async () => {
        try {
          await archiveCourse(courseId);
        } catch (archiveError) {
          toast("error", getApiErrorMessage(archiveError, "Не удалось удалить курс."));
          return false;
        }
        const store = useDndCourseStore.getState();
        if (store.course?.id === courseId) store.resetAll({ silent: true });
        toast("success", "Курс удалён");
        navigate("/drag-and-drop-course", { replace: true });
        return true;
      },
    });

  const startNew = () => {
    useDndCourseStore.getState().resetAll({ silent: true });
    navigate("/drag-and-drop-course");
  };

  const statusInfo = STATUS[status] || null;
  const course = data?.course;
  const sectionLabel = active ? "Урок" : activeModule ? "Модуль" : "Курс";
  const sectionTitle = active?.title || activeModule?.title || course?.title || "";

  return (
    <div className="dnd-preview-page">
      <section className="dnd-builder dnd-preview" aria-label="Просмотр курса">
        <header className="dnd-preview-bar">
          <button type="button" className="dnd-btn dnd-btn--ghost" onClick={backToBuilder} disabled={action === "builder"}>
            {action === "builder" ? <Spinner size={14} /> : <Icon name="arrowLeft" size={16} />}
            Вернуться в конструктор
          </button>
          <div className="dnd-preview-bar-title">
            <span className="dnd-eyebrow">Просмотр курса</span>
            {statusInfo ? (
              <StatusPill tone={statusInfo.tone} icon={status === "published" ? "check" : null}>
                {statusInfo.label}
              </StatusPill>
            ) : null}
          </div>
          <div className="dnd-preview-actions">
            {status !== "published" && status !== "archived" ? (
              <button type="button" className="dnd-btn dnd-btn--accent" onClick={() => changeStatus("publish")} disabled={Boolean(action) || !data}>
                {action === "publish" ? <Spinner size={14} /> : <Icon name="flag" size={16} />}
                {action === "publish" ? "Публикуем…" : "Опубликовать"}
              </button>
            ) : null}
            {status !== "invite_only" && status !== "archived" ? (
              <button type="button" className="dnd-btn dnd-btn--ghost" onClick={() => changeStatus("invite_only")} disabled={Boolean(action) || !data}>
                {action === "invite_only" ? <Spinner size={14} /> : <Icon name="link" size={16} />}
                {action === "invite_only" ? "Сохраняем…" : "Только по приглашению"}
              </button>
            ) : null}
            <ActionMenu
              label="Ещё действия"
              buttonClassName="dnd-icon-btn"
              align="end"
              items={[
                { key: "student", icon: "eye", label: "Открыть как студент", onSelect: () => navigate(`/course/${courseId}`) },
                { key: "new", icon: "plus", label: "Создать новый курс", onSelect: startNew },
                { key: "sep", type: "separator" },
                { key: "delete", icon: "trash", label: "Удалить курс", danger: true, onSelect: removeCourse, disabled: status === "archived" },
              ]}
            />
          </div>
        </header>

        {error ? (
          <div className="dnd-preview-state">
            <p className="dnd-inline-error" role="alert">
              <Icon name="alert" size={16} />
              <span>{error}</span>
              <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={load}>
                <Icon name="retry" size={14} /> Повторить
              </button>
            </p>
          </div>
        ) : !data ? (
          <div className="dnd-preview-state" role="status">
            <Spinner size={18} /> Загружаем курс…
          </div>
        ) : null}
        <ConfirmDialog />
        <Toasts />
        <DndTooltipLayer />
      </section>

      {data && !error ? (
        <section className="container section lesson-view generated-course-learning-view dnd-preview-learning">
          <SectionTop label={sectionLabel} title={sectionTitle} />
          <div className="lesson-view-grid generated-course-learning-grid">
            {treeCourse.blocks.length ? (
              <CourseNavigationTree
                selectedCourse={treeCourse}
                selectedBlock={activeModule || treeCourse.blocks[0]}
                selectedLessonId={activeLessonId || ""}
                selectedPracticeId=""
                completedLessons={{}}
                completedPractices={{}}
                openBlock={openBlock}
                openLesson={openLesson}
                openPractice={() => {}}
                mode="theory"
              />
            ) : (
              <aside className="course-nav-tree generated-course-navigation-shell">
                <p className="course-viewer-muted">В курсе пока нет модулей.</p>
              </aside>
            )}

            <article className="glass-card lesson-main-card generated-course-main-card">
              <div className="lesson-scroll-frame generated-course-scroll-frame">
                {active || activeModule ? (
                  <button type="button" className="btn btn-outline dnd-preview-back" onClick={active ? () => setActiveLessonId(null) : openOverview}>
                    <Icon name="arrowLeft" size={15} /> {active ? "К модулю" : "О курсе"}
                  </button>
                ) : null}
                {active ? (
                  <div className="lesson-theory-content">
                    <p className="course-category">{course.title}</p>
                    <LessonBasicInfo
                      lesson={{
                        ...active,
                        order: active.lessonIndex,
                        estimated_time_minutes: active.estimatedTimeMinutes ?? null,
                      }}
                    />
                    {lessonError ? (
                      <p className="course-viewer-muted" role="alert">
                        {lessonError}
                      </p>
                    ) : lessonBlocks[active.id] ? (
                      <ContentBlocks blocks={lessonBlocks[active.id]} ownerUserId={user?.id} />
                    ) : (
                      <p className="course-viewer-muted" role="status">
                        Загружаем теорию урока…
                      </p>
                    )}
                    <div className="generated-course-actions dnd-preview-pager">
                      <button type="button" className="btn btn-outline" disabled={activeIndex <= 0} onClick={() => openLesson(flatLessons[activeIndex - 1]?.id)}>
                        <Icon name="arrowLeft" size={15} /> Предыдущий урок
                      </button>
                      <button type="button" className="btn btn-solid" disabled={activeIndex >= flatLessons.length - 1} onClick={() => openLesson(flatLessons[activeIndex + 1]?.id)}>
                        Следующий урок <Icon name="arrowRight" size={15} />
                      </button>
                    </div>
                  </div>
                ) : activeModule ? (
                  <>
                    <ModuleBasicInfo module={activeModule} />
                    <LessonList
                      lessons={activeModule.lessons.map((lesson, index) => ({ ...lesson, order: index }))}
                      selectedLessonId=""
                      onSelectLesson={openLesson}
                    />
                  </>
                ) : (
                  <>
                    <CourseBasicInfo course={treeCourse} />
                    <ModuleList
                      modules={treeCourse.blocks.map((module, index) => ({ ...module, order: index }))}
                      selectedModuleId=""
                      disabled={false}
                      onSelectModule={openBlock}
                    />
                  </>
                )}
              </div>
            </article>
          </div>
        </section>
      ) : null}
    </div>
  );
}
