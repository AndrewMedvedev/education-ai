import { forwardRef, useId, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ContentPreviewModal from "../ContentPreviewModal";
import ContentBlockSources, { hasSources } from "./ContentBlockSources";
import MermaidDiagram from "../MermaidDiagram";
import SyntaxHighlightedCode from "../SyntaxHighlightedCode";
import { getMediaUrl, MEDIA_FOLDERS } from "../../utils/media";
import { normalizeQuizQuestions } from "../../utils/quiz";

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

const createMarkdownComponents = (onPreview, lessonId, blockId) => ({
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    const language = match?.[1]?.toLowerCase();
    const code = String(children).replace(/\n$/, "");

    if (language === "mermaid") {
      return (
        <button
          type="button"
          className="content-preview-trigger content-preview-diagram-trigger"
          onClick={() => onPreview({ type: "diagram", chart: code, lessonId, blockId })}
          aria-label="Открыть схему для подробного просмотра"
        >
          <MermaidDiagram chart={code} lessonId={lessonId} blockId={blockId} />
        </button>
      );
    }

    return (
      <SyntaxHighlightedCode className={className} {...props}>
        {children}
      </SyntaxHighlightedCode>
    );
  },
});

const getTextContent = (block) => {
  const candidates = [
    block?.md_content,
    block?.content,
    block?.text,
    block?.markdown,
    block?.code,
    block?.explanation,
  ];

  return (
    candidates.find((value) => typeof value === "string" && value.trim()) ?? ""
  );
};

function TextBlock({ block, index, onPreview, lessonId }) {
  const text = getTextContent(block);

  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">Блок {index + 1} · текст</div>
      {block.title && <h3>{block.title}</h3>}
      {text ? (
        <div className="lesson-markdown content-block-markdown">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={createMarkdownComponents(onPreview, lessonId, index)}
            urlTransform={safeMarkdownUrl}
          >
            {text}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="course-viewer-muted">Текстовый блок пуст.</p>
      )}
    </article>
  );
}

// В текстах квиза встречается markdown-выделение **так**: показываем его жирным,
// а не звёздочками. Полный markdown здесь не нужен.
const renderQuizInline = (text) =>
  String(text ?? "")
    .split(/\*\*(.+?)\*\*/g)
    .map((part, partIndex) =>
      partIndex % 2 === 1 ? <strong key={partIndex}>{part}</strong> : part,
    );

const stripQuizMarkup = (text) => String(text ?? "").replace(/\*\*(.+?)\*\*/g, "$1");

function QuizBlock({ block, index, lessonId }) {
  const questions = normalizeQuizQuestions(block, lessonId);
  const reactId = useId();
  const quizId = String(reactId).replace(/[^a-zA-Z0-9_-]/g, "");
  const [expandedQuestions, setExpandedQuestions] = useState({});

  const toggleQuestion = (questionIndex) => {
    setExpandedQuestions((current) => ({
      ...current,
      [questionIndex]: !current[questionIndex],
    }));
  };

  const answerableIndexes = questions
    .map((question, questionIndex) => (question.answer || question.explanation ? questionIndex : -1))
    .filter((questionIndex) => questionIndex >= 0);
  const allExpanded =
    answerableIndexes.length > 0 &&
    answerableIndexes.every((questionIndex) => expandedQuestions[questionIndex]);
  const toggleAll = () => {
    setExpandedQuestions(
      allExpanded ? {} : Object.fromEntries(answerableIndexes.map((questionIndex) => [questionIndex, true])),
    );
  };

  if (!questions.length) return null;

  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">Блок {index + 1} · quiz</div>
      <div className="quiz-block-head">
        <h3>{block.title || "Проверочные вопросы"}</h3>
        {answerableIndexes.length > 1 && (
          <button type="button" className="quiz-toggle-all" onClick={toggleAll} aria-pressed={allExpanded}>
            {allExpanded ? "Скрыть все ответы" : "Показать все ответы"}
          </button>
        )}
      </div>
        <ol className="quiz-question-list">
          {questions.map((question, questionIndex) => {
            const title = question.question;
            const hasAnswerDetails = Boolean(question.answer || question.explanation);
            const isExpanded = Boolean(expandedQuestions[questionIndex]);
            const answerId = `quiz-answer-${quizId}-${index}-${questionIndex}`;

            return (
              <li key={`question-${questionIndex}`}>
                <button
                  type="button"
                  className="quiz-question-toggle"
                  aria-expanded={isExpanded}
                  aria-controls={hasAnswerDetails ? answerId : undefined}
                  onClick={() => toggleQuestion(questionIndex)}
                >
                  <strong>{stripQuizMarkup(title)}</strong>
                  <span aria-hidden="true">
                    {isExpanded ? "Скрыть ответ" : "Показать ответ"}
                  </span>
                </button>
                {question.options.length > 0 && (
                  <ul className="quiz-answer-options">
                    {question.options.map((option, optionIndex) => (
                      <li key={`option-${optionIndex}`}>{renderQuizInline(option)}</li>
                    ))}
                  </ul>
                )}
                {hasAnswerDetails && isExpanded && (
                  <div id={answerId} className="quiz-answer-details">
                    {question.answer && <p><strong>Ответ:</strong> {renderQuizInline(question.answer)}</p>}
                    {question.explanation && <p><strong>Пояснение:</strong> {renderQuizInline(question.explanation)}</p>}
                  </div>
                )}
              </li>
            );
          })}
        </ol>
    </article>
  );
}

function VideoBlock({ block, index }) {
  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">Блок {index + 1} · видео</div>
      {block.url ? (
        <a href={safeMarkdownUrl(block.url)} target="_blank" rel="noreferrer">
          Открыть видео
        </a>
      ) : (
        <p className="course-viewer-muted">Ссылка на видео не указана.</p>
      )}
      {block.description && (
        <p className="course-viewer-muted">{block.description}</p>
      )}
    </article>
  );
}

function ImageBlock({ block, index, ownerUserId }) {
  const imageUrl = block.image_id
    ? getMediaUrl(ownerUserId, MEDIA_FOLDERS.COURSE_IMAGES, block.image_id)
    : block.image_url;
  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">
        Блок {index + 1} · изображение
      </div>
      {imageUrl ? (
        <img
          className="content-block-image"
          src={safeMarkdownUrl(imageUrl)}
          alt=""
        />
      ) : (
        <p className="course-viewer-muted">Изображение не указано.</p>
      )}
    </article>
  );
}

function MermaidBlock({ block, index, onPreview, lessonId }) {
  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">Блок {index + 1} · mermaid</div>
      {block.title && <h3>{block.title}</h3>}
      {block.md_content ? (
        <button
          type="button"
          className="content-preview-trigger content-preview-diagram-trigger"
          onClick={() =>
            onPreview({
              type: "diagram",
              chart: block.md_content,
              lessonId,
              blockId: index,
            })
          }
          aria-label={`Открыть схему${block.title ? `: ${block.title}` : ""}`}
        >
          <MermaidDiagram chart={block.md_content} lessonId={lessonId} blockId={index} />
        </button>
      ) : (
        <p className="course-viewer-muted">Код диаграммы отсутствует.</p>
      )}
      {block.explanation && (
        <p className="course-viewer-muted">{block.explanation}</p>
      )}
    </article>
  );
}

function FormulaBlock({ block, index, label }) {
  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">
        Блок {index + 1} · {label}
      </div>
      {block.formula ? (
        <pre className="content-block-pre">{block.formula}</pre>
      ) : (
        <p className="course-viewer-muted">Формула не указана.</p>
      )}
      {block.explanation && (
        <p className="course-viewer-muted">{block.explanation}</p>
      )}
    </article>
  );
}

function CodeBlock({ block, index }) {
  const code = typeof block?.code === "string" ? block.code : "";

  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">
        Блок {index + 1} · код{block.language ? ` · ${block.language}` : ""}
      </div>
      {block.title && <h3>{block.title}</h3>}
      {code ? (
        <pre className="content-block-code">{code}</pre>
      ) : (
        <p className="course-viewer-muted">Код в блоке отсутствует.</p>
      )}
      {typeof block.explanation === "string" && block.explanation && (
        <p className="course-viewer-muted">{block.explanation}</p>
      )}
    </article>
  );
}

function UnsupportedBlock({ block, index }) {
  return (
    <article className="content-block-card content-block-unsupported">
      <div className="course-viewer-eyebrow">Блок {index + 1}</div>
      <h3>Тип блока не поддерживается</h3>
      <p className="course-viewer-muted">
        Не удалось безопасно отобразить блок типа "
        {block?.content_type || "unknown"}".
      </p>
    </article>
  );
}

function getBlockContentType(block) {
  const rawType = String(
    block?.content_type ||
      block?.contentType ||
      block?.block_type ||
      block?.type ||
      "text",
  ).toLowerCase();
  const aliases = {
    markdown: "text",
    md: "text",
    theory: "text",
    lecture: "text",
    code: "program_code",
    program: "program_code",
    diagram: "mermaid",
    question: "quiz",
    questions: "quiz",
    test: "quiz",
  };

  return aliases[rawType] || rawType;
}

function renderContentBlock(block, index, onPreview, ownerUserId, lessonId) {
  const normalizedBlock = {
    ...block,
    content_type: getBlockContentType(block),
  };

  switch (normalizedBlock.content_type) {
    case "text":
      return (
        <TextBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
          onPreview={onPreview}
          lessonId={lessonId}
        />
      );
    case "video":
      return (
        <VideoBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
        />
      );
    case "image":
      return (
        <ImageBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
          ownerUserId={ownerUserId}
        />
      );
    case "quiz":
      return (
        <QuizBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
          lessonId={lessonId}
        />
      );
    case "program_code":
      return (
        <CodeBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
        />
      );
    case "mermaid":
      return (
        <MermaidBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
          onPreview={onPreview}
          lessonId={lessonId}
        />
      );
    case "math_formula":
      return (
        <FormulaBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
          label="формула"
        />
      );
    case "chemical_formula":
      return (
        <FormulaBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
          label="химия"
        />
      );
    case "musical_notation":
      return (
        <FormulaBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
          label="ноты"
        />
      );
    default:
      return (
        <UnsupportedBlock
          key={`content-${index}`}
          block={normalizedBlock}
          index={index}
        />
      );
  }
}

const ContentBlocks = forwardRef(function ContentBlocks(
  { blocks, ownerUserId, lessonId },
  ref,
) {
  const [preview, setPreview] = useState(null);

  if (!Array.isArray(blocks) || blocks.length === 0) {
    return (
      <article ref={ref} className="course-viewer-card theory-section">
        <h2>Теория урока</h2>
        <p className="course-viewer-muted">
          В уроке пока нет теоретических блоков.
        </p>
      </article>
    );
  }

  return (
    <section
      className="course-viewer-card theory-section"
      aria-labelledby="theory-title"
    >
      <h2 id="theory-title">Теория урока</h2>
      <div ref={ref} className="content-blocks-list">
        {blocks.map((block, index) =>
          hasSources(block?.sources) ? (
            <div key={`content-${index}`} className="content-block-with-sources">
              {renderContentBlock(
                block,
                index,
                setPreview,
                ownerUserId,
                lessonId,
              )}
              <ContentBlockSources sources={block.sources} />
            </div>
          ) : (
            renderContentBlock(block, index, setPreview, ownerUserId, lessonId)
          ),
        )}
      </div>
      <ContentPreviewModal preview={preview} onClose={() => setPreview(null)} />
    </section>
  );
});

export default ContentBlocks;
