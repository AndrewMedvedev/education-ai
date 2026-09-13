// Страница отдельного урока с навигацией по курсу и блочным редактором контента
import { useEffect, useRef, useState } from "react";
import CourseNavigationTree from "../components/CourseNavigationTree";
import ContentBlocks from "../components/course/ContentBlocks";
import {
  LessonPracticeAgent,
  LessonTestAgent,
} from "../components/LessonAgentAssessments";
import LessonChatWorkspace from "../components/LessonChatWorkspace";
import LessonContentEditor from "../components/LessonContentEditor";
import SectionTop from "../components/SectionTop";
import { getLessonContentBlocks } from "../services/courseService";
import { useGoBack } from "../hooks/useGoBack";
import { useTheorySessionTracker } from "../hooks/useTheorySessionTracker";
import { useUiLayoutStore } from "../stores/uiLayoutStore";
import { printLessonSummary } from "../utils/printLessonSummary";

export default function LessonPage({
  selectedCourse,
  selectedBlock,
  selectedLesson,
  completedLessons,
  completedPractices,
  openBlock,
  openLesson,
  openPractice,
  isCourseEditMode,
  updateLesson,
}) {
  const hasContent = Boolean(selectedLesson.markdown || selectedLesson.content);
  const persistedActiveTab = useUiLayoutStore((state) =>
    state.getLessonActiveTab(selectedLesson.id),
  );
  const setLessonActiveTab = useUiLayoutStore(
    (state) => state.setLessonActiveTab,
  );
  const [contentBlocks, setContentBlocks] = useState([]);
  const [contentBlocksLessonId, setContentBlocksLessonId] = useState("");
  const [isLoadingTheory, setIsLoadingTheory] = useState(false);
  const [theoryError, setTheoryError] = useState("");
  const theoryContainerRef = useRef(null);
  const theoryContentRef = useRef(null);
  const showStudentTabs = !isCourseEditMode;
  const activeTab = showStudentTabs ? persistedActiveTab : "theory";
  const isChatAvailable = !isCourseEditMode && activeTab === "theory";
  const lessonContentBlocks = Array.isArray(selectedLesson.contentBlocks)
    ? selectedLesson.contentBlocks
    : Array.isArray(selectedLesson.content_blocks)
      ? selectedLesson.content_blocks
      : [];
  const visibleContentBlocks = contentBlocks.length
    ? contentBlocks
    : lessonContentBlocks.length
      ? lessonContentBlocks
      : hasContent
        ? [
            {
              content_type: "text",
              ai_generated: false,
              md_content: selectedLesson.markdown || selectedLesson.content,
            },
          ]
        : [];
  const editorLesson = isCourseEditMode
    ? {
        ...selectedLesson,
        contentBlocks: visibleContentBlocks,
        content_blocks: visibleContentBlocks,
      }
    : selectedLesson;
  const isEditorWaitingForTheory =
    isCourseEditMode &&
    isLoadingTheory &&
    contentBlocksLessonId !== selectedLesson.id &&
    lessonContentBlocks.length === 0 &&
    !hasContent;

  const shouldTrackTheorySession = !isCourseEditMode && activeTab === "theory";
  const goBack = useGoBack({
    fallbackPath: isCourseEditMode
      ? `/course/${selectedCourse.id}/edit/block/${selectedBlock.id}`
      : `/course/${selectedCourse.id}/block/${selectedBlock.id}`,
  });

  useTheorySessionTracker(selectedLesson.id, {
    enabled: shouldTrackTheorySession,
    scrollContainerRef: theoryContainerRef,
    contentRef: theoryContentRef,
    isContentReady: !isLoadingTheory && !theoryError,
  });

  useEffect(() => {
    if (!selectedLesson.id) {
      setContentBlocks([]);
      setContentBlocksLessonId("");
      setTheoryError("");
      return;
    }

    let isMounted = true;
    setContentBlocks([]);
    setContentBlocksLessonId("");
    setIsLoadingTheory(true);
    setTheoryError("");

    getLessonContentBlocks(selectedLesson.id)
      .then((blocks) => {
        if (isMounted) {
          setContentBlocks(blocks);
          setContentBlocksLessonId(selectedLesson.id);
        }
      })
      .catch((error) => {
        if (isMounted) {
          setTheoryError(
            error.userMessage ||
              error.message ||
              "Не удалось загрузить теорию урока.",
          );
          setContentBlocks([]);
          setContentBlocksLessonId(selectedLesson.id);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingTheory(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedLesson.id]);

  return (
    <section
      className={`container section lesson-view ${
        isCourseEditMode ? "is-course-edit-layout" : "is-learning-layout"
      }`}
    >
      <SectionTop label="Урок" title={selectedLesson.title} />
      <button
        type="button"
        className="btn btn-outline back-btn"
        onClick={goBack}
        aria-label="Назад к блоку"
        title="Назад к блоку"
      >
        &lt;
      </button>
      <LessonChatWorkspace
        className={
          isCourseEditMode ? "is-course-edit-layout" : "is-learning-layout"
        }
        chatEnabled={!isCourseEditMode}
        chatAvailable={isChatAvailable}
        chatKey={selectedLesson.id}
        chatProps={{
          courseId: selectedCourse.id,
          lessonId: selectedLesson.id,
          lessonTitle: selectedLesson.title,
          contentBlocks: visibleContentBlocks,
          onDownloadSummary: () =>
            printLessonSummary({
              course: selectedCourse,
              block: selectedBlock,
              lesson: selectedLesson,
            }),
        }}
      >
        <CourseNavigationTree
          selectedCourse={selectedCourse}
          selectedBlock={selectedBlock}
          selectedLessonId={selectedLesson.id}
          selectedPracticeId=""
          completedLessons={completedLessons}
          completedPractices={completedPractices}
          openBlock={openBlock}
          openLesson={openLesson}
          openPractice={openPractice}
          mode="theory"
        />
        <article
          ref={theoryContainerRef}
          className={`glass-card lesson-main-card ${isCourseEditMode ? "is-editing" : ""}`}
          onScroll={(event) => {
            event.currentTarget.classList.toggle(
              "is-scrolled",
              event.currentTarget.scrollTop > 8,
            );
          }}
        >
          <div className="lesson-scroll-frame">
            <div
              className="lesson-mode-switch"
              role="tablist"
              aria-label="Тип материала"
            >
              <button
                type="button"
                className={activeTab === "theory" ? "is-active" : ""}
                aria-selected={activeTab === "theory"}
                onClick={() => setLessonActiveTab(selectedLesson.id, "theory")}
              >
                Теория
              </button>
              {showStudentTabs && (
                <>
                  <button
                    type="button"
                    className={activeTab === "questions" ? "is-active" : ""}
                    aria-selected={activeTab === "questions"}
                    onClick={() =>
                      setLessonActiveTab(selectedLesson.id, "questions")
                    }
                  >
                    Проверочные вопросы
                  </button>
                  <button
                    type="button"
                    className={activeTab === "practice" ? "is-active" : ""}
                    aria-selected={activeTab === "practice"}
                    onClick={() =>
                      setLessonActiveTab(selectedLesson.id, "practice")
                    }
                    disabled={!selectedBlock.id || !selectedLesson.id}
                  >
                    Практика
                  </button>
                </>
              )}
            </div>
            {showStudentTabs && activeTab === "questions" ? (
              <LessonTestAgent
                key={`${selectedBlock.id}:${selectedLesson.id}:test`}
                moduleId={selectedBlock.id}
                lessonId={selectedLesson.id}
              />
            ) : showStudentTabs && activeTab === "practice" ? (
              <LessonPracticeAgent
                key={`${selectedBlock.id}:${selectedLesson.id}:practice`}
                moduleId={selectedBlock.id}
                lessonId={selectedLesson.id}
              />
            ) : (
              <>
                {isCourseEditMode && (
                  <div className="course-editor-panel lesson-editor-panel">
                    <div className="course-editor-grid">
                      <label className="course-editor-field">
                        <span>Название урока</span>
                        <input
                          value={selectedLesson.title}
                          onChange={(event) =>
                            updateLesson(selectedLesson.id, {
                              title: event.target.value,
                            })
                          }
                        />
                      </label>
                      <label className="course-editor-field">
                        <span>Длительность</span>
                        <input
                          value={selectedLesson.duration}
                          onChange={(event) =>
                            updateLesson(selectedLesson.id, {
                              duration: event.target.value,
                            })
                          }
                        />
                      </label>
                      <label className="course-editor-field course-editor-field-wide">
                        <span>Краткое описание</span>
                        <textarea
                          value={selectedLesson.summary || ""}
                          onChange={(event) =>
                            updateLesson(selectedLesson.id, {
                              summary: event.target.value,
                            })
                          }
                        />
                      </label>
                    </div>

                    {isEditorWaitingForTheory ? (
                      <p className="course-viewer-muted">
                        Загружаем теорию урока...
                      </p>
                    ) : theoryError ? (
                      <article
                        className="glass-card course-viewer-error"
                        role="alert"
                      >
                        {theoryError}
                      </article>
                    ) : (
                      <LessonContentEditor
                        key={`${selectedLesson.id}:${contentBlocksLessonId}`}
                        courseId={selectedCourse.id}
                        lesson={editorLesson}
                        onChange={(changes) =>
                          updateLesson(selectedLesson.id, changes)
                        }
                      />
                    )}
                  </div>
                )}

                {!isCourseEditMode && isLoadingTheory ? (
                  <p className="course-viewer-muted">
                    Загружаем теорию урока...
                  </p>
                ) : !isCourseEditMode && theoryError ? (
                  <article
                    className="glass-card course-viewer-error"
                    role="alert"
                  >
                    {theoryError}
                  </article>
                ) : !isCourseEditMode ? (
                  <div className="lesson-theory-content">
                    <p className="course-category">{selectedCourse.title}</p>
                    <p className="lesson-summary">{selectedLesson.summary}</p>
                    <ContentBlocks
                      ref={theoryContentRef}
                      blocks={visibleContentBlocks}
                    />
                  </div>
                ) : null}
              </>
            )}
          </div>
        </article>
      </LessonChatWorkspace>
    </section>
  );
}
