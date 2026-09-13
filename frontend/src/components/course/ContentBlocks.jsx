import { forwardRef, useId, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ContentPreviewModal from "../ContentPreviewModal";
import MermaidDiagram from "../MermaidDiagram";
import SyntaxHighlightedCode from "../SyntaxHighlightedCode";
import { getMediaUrl, MEDIA_FOLDERS } from "../../utils/media";

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

const createMarkdownComponents = (onPreview) => ({
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    const language = match?.[1]?.toLowerCase();
    const code = String(children).replace(/\n$/, "");

    if (language === "mermaid") {
      return (
        <button
          type="button"
          className="content-preview-trigger content-preview-diagram-trigger"
          onClick={() => onPreview({ type: "diagram", chart: code })}
          aria-label="Открыть схему для подробного просмотра"
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

function TextBlock({ block, index, onPreview }) {
  const text = getTextContent(block);

  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">Блок {index + 1} · текст</div>
      {block.title && <h3>{block.title}</h3>}
      {text ? (
        <div className="lesson-markdown content-block-markdown">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={createMarkdownComponents(onPreview)}
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

const normalizeQuizQuestions = (block) => {
  const sourceQuestions = block?.questions;

  if (Array.isArray(sourceQuestions)) {
    return sourceQuestions.map((question) => {
      if (Array.isArray(question)) {
        return {
          title: typeof question[0] === "string" ? question[0] : "Вопрос",
          answer: question.slice(1).filter(Boolean).join("\n"),
        };
      }

      if (question && typeof question === "object") {
        const options = Array.isArray(question.options)
          ? question.options.join("\n")
          : question.options;
        const answerParts = [options, question.answer].filter(Boolean);

        return {
          title:
            typeof question.question === "string" && question.question.trim()
              ? question.question
              : "Вопрос",
          answer: answerParts.join("\n\n"),
        };
      }

      return {
        title: typeof question === "string" ? question : "Вопрос",
        answer: "",
      };
    });
  }

  if (sourceQuestions && typeof sourceQuestions === "object") {
    const options = Array.isArray(sourceQuestions.options)
      ? sourceQuestions.options.join("\n")
      : sourceQuestions.options;
    const answerParts = [options, sourceQuestions.answer].filter(Boolean);

    return [
      {
        title:
          typeof sourceQuestions.question === "string" &&
          sourceQuestions.question.trim()
            ? sourceQuestions.question
            : "Вопрос",
        answer: answerParts.join("\n\n"),
      },
    ];
  }

  return [];
};

function QuizBlock({ block, index }) {
  const questions = normalizeQuizQuestions(block);
  const reactId = useId();
  const quizId = String(reactId).replace(/[^a-zA-Z0-9_-]/g, "");
  const [expandedQuestions, setExpandedQuestions] = useState({});

  const toggleQuestion = (questionIndex) => {
    setExpandedQuestions((current) => ({
      ...current,
      [questionIndex]: !current[questionIndex],
    }));
  };

  return (
    <article className="content-block-card">
      <div className="course-viewer-eyebrow">Блок {index + 1} · quiz</div>
      <h3>{block.title || "Проверочные вопросы"}</h3>
      {questions.length > 0 ? (
        <ol className="quiz-question-list">
          {questions.map((question, questionIndex) => {
            const title = question.title;
            const details = question.answer;
            const isExpanded = Boolean(expandedQuestions[questionIndex]);
            const answerId = `quiz-answer-${quizId}-${index}-${questionIndex}`;

            return (
              <li key={`question-${questionIndex}`}>
                <button
                  type="button"
                  className="quiz-question-toggle"
                  aria-expanded={isExpanded}
                  aria-controls={details ? answerId : undefined}
                  onClick={() => toggleQuestion(questionIndex)}
                >
                  <strong>{title}</strong>
                  <span aria-hidden="true">
                    {isExpanded ? "Скрыть" : "Показать"}
                  </span>
                </button>
                {details && isExpanded && (
                  <pre id={answerId} className="content-block-pre">
                    {details}
                  </pre>
                )}
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="course-viewer-muted">Вопросы в quiz-блоке отсутствуют.</p>
      )}
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

function MermaidBlock({ block, index, onPreview }) {
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
            })
          }
          aria-label={`Открыть схему${block.title ? `: ${block.title}` : ""}`}
        >
          <MermaidDiagram chart={block.md_content} />
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

function renderContentBlock(block, index, onPreview, ownerUserId) {
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
  { blocks, ownerUserId },
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
          renderContentBlock(block, index, setPreview, ownerUserId),
        )}
      </div>
      <ContentPreviewModal preview={preview} onClose={() => setPreview(null)} />
    </section>
  );
});

export default ContentBlocks;
