// Страница практического задания курса с навигацией по курсу
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ContentPreviewModal from "../components/ContentPreviewModal";
import CourseNavigationTree from "../components/CourseNavigationTree";
import {
  LessonPracticeAgent,
  LessonTestAgent,
} from "../components/LessonAgentAssessments";

import MermaidDiagram from "../components/MermaidDiagram";
import SectionTop from "../components/SectionTop";
import SyntaxHighlightedCode from "../components/SyntaxHighlightedCode";
import { useGoBack } from "../hooks/useGoBack";

const allowedImageDataUrl =
  /^data:image\/(?:png|jpeg|webp|gif);base64,[a-z0-9+/=]+$/i;

function safeMarkdownUrl(url) {
  const value = String(url || "").trim();
  if (allowedImageDataUrl.test(value)) {
    return value;
  }
  if (/^(https?:|mailto:|tel:)/i.test(value)) {
    return value;
  }
  if (/^(\/|\.{1,2}\/|#)/.test(value)) {
    return value;
  }
  return value.includes(":") ? "" : value;
}

export default function PracticePage({
  selectedCourse,
  selectedBlock,
  selectedPractice,
  completedLessons,
  completedPractices,
  togglePracticeComplete,
  openBlock,
  openLesson,
  openPractice,
  isCourseEditMode,
}) {
  const [preview, setPreview] = useState(null);
  const [activeTab, setActiveTab] = useState("practice");
  const goBack = useGoBack({
    fallbackPath: isCourseEditMode
      ? `/course/${selectedCourse.id}/edit/block/${selectedBlock.id}`
      : `/course/${selectedCourse.id}/block/${selectedBlock.id}`,
  });

  const markdownComponents = {
    code({ className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || "");
      const language = match?.[1]?.toLowerCase();
      const code = String(children).replace(/\n$/, "");

      if (language === "mermaid") {
        return (
          <button
            type="button"
            className="content-preview-trigger content-preview-diagram-trigger"
            onClick={() => setPreview({ type: "diagram", chart: code })}
            aria-label="Увеличить схему"
          >
            <MermaidDiagram chart={code} />
          </button>
        );
      }

      return (
        <SyntaxHighlightedCode className={className} {...props}>
          {children}
        </SyntaxHighlightedCode>
      );
    },
    img({ src, alt }) {
      return (
        <button
          type="button"
          className="content-preview-trigger content-preview-image-trigger"
          onClick={() => setPreview({ type: "image", src, alt })}
          aria-label={`Увеличить изображение${alt ? `: ${alt}` : ""}`}
        >
          <img src={src} alt={alt || ""} />
        </button>
      );
    },
    table({ children }) {
      return (
        <div
          className="content-preview-table-trigger"
          role="button"
          tabIndex={0}
          onClick={() => setPreview({ type: "table", children })}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              setPreview({ type: "table", children });
            }
          }}
          aria-label="Увеличить таблицу"
        >
          <table>{children}</table>
        </div>
      );
    },
  };

  return (
    <section className="container section practice-view">
      <SectionTop label="Практика" title={selectedPractice.title} />
      <button
        type="button"
        className="btn btn-outline back-btn"
        onClick={goBack}
        aria-label="Назад к блоку"
        title="Назад к блоку"
      >
        &lt;
      </button>
      <div className="practice-view-grid">
        <CourseNavigationTree
          selectedCourse={selectedCourse}
          selectedBlock={selectedBlock}
          selectedLessonId=""
          selectedPracticeId={selectedPractice.id}
          completedLessons={completedLessons}
          completedPractices={completedPractices}
          openBlock={openBlock}
          openLesson={openLesson}
          openPractice={openPractice}
          mode={isCourseEditMode ? "theory" : "practice"}
        />
        <article className="glass-card practice-main-card">
          {!isCourseEditMode && (
            <div
              className="lesson-mode-switch"
              role="tablist"
              aria-label="Тип материала"
            >
              <button
                type="button"
                aria-selected="false"
                onClick={() => openLesson(selectedBlock.lessons[0]?.id)}
                disabled={!selectedBlock.lessons[0]}
              >
                Теория
              </button>
              <button
                type="button"
                className={activeTab === "questions" ? "is-active" : ""}
                aria-selected={activeTab === "questions"}
                onClick={() => setActiveTab("questions")}
              >
                Проверочные вопросы
              </button>
              <button
                type="button"
                className={activeTab === "practice" ? "is-active" : ""}
                aria-selected={activeTab === "practice"}
                onClick={() => setActiveTab("practice")}
              >
                Практика
              </button>
            </div>
          )}
          {!isCourseEditMode && activeTab === "questions" ? (
            <LessonTestAgent
              key={`${selectedBlock.id}:${selectedBlock.lessons[0]?.id}:test`}
              moduleId={selectedBlock.id}
              lessonId={selectedBlock.lessons[0]?.id}
            />
          ) : !isCourseEditMode && activeTab === "practice" ? (
            <LessonPracticeAgent
              key={`${selectedBlock.id}:${selectedBlock.lessons[0]?.id}:practice`}
              moduleId={selectedBlock.id}
              lessonId={selectedBlock.lessons[0]?.id}
            />
          ) : (
            <>
              {!isCourseEditMode && (
                <p className="course-category">{selectedCourse.title}</p>
              )}
              {isCourseEditMode && (
                <p className="course-viewer-muted">
                  Редактирование практики в конструкторе отключено.
                </p>
              )}
              {!isCourseEditMode && selectedPractice.markdown ? (
                <div className="practice-markdown lesson-markdown">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                    urlTransform={safeMarkdownUrl}
                  >
                    {selectedPractice.markdown}
                  </ReactMarkdown>
                </div>
              ) : !isCourseEditMode ? (
                <p className="lesson-content">
                  Результат: {selectedPractice.result}
                </p>
              ) : null}
              {!isCourseEditMode && (
                <div className="lesson-controls">
                  <span className="lesson-time">
                    {selectedPractice.duration}
                  </span>
                </div>
              )}
            </>
          )}
        </article>
      </div>
      <ContentPreviewModal preview={preview} onClose={() => setPreview(null)} />
    </section>
  );
}
