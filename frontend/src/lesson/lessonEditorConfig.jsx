import MermaidDiagram from "../components/MermaidDiagram";
import SyntaxHighlightedCode from "../components/SyntaxHighlightedCode";
import { getMediaId } from "../utils/media";

export const MAX_CONTENT_BLOCKS = 10;

export const blockTypes = [
  {
    id: "text",
    contentType: "text",
    label: "Текст",
    hint: "Markdown-лекция",
    template: { md_content: "Новый текстовый блок." },
  },
  {
    id: "video",
    contentType: "video",
    label: "Видео",
    hint: "Ссылка и описание",
    template: { url: "", description: "" },
  },
  {
    id: "image",
    contentType: "image",
    label: "Изображение",
    hint: "Файл в хранилище",
    template: { image_id: "" },
  },
  {
    id: "program_code",
    contentType: "program_code",
    label: "Код",
    hint: "Язык, код и пояснение",
    template: { language: "python", code: "", explanation: "" },
  },
  {
    id: "mermaid",
    contentType: "mermaid",
    label: "Схема",
    hint: "Mermaid-диаграмма",
    template: {
      title: "Новая диаграмма",
      md_content: "flowchart TD\n  A[Начало] --> B[Шаг]",
      explanation: "",
    },
  },
  {
    id: "quiz",
    contentType: "quiz",
    label: "Quiz",
    hint: "Вопросы и ответы",
    template: { questions: [{ question: "", answer: "" }] },
  },
  {
    id: "math_formula",
    contentType: "math_formula",
    label: "Формула",
    hint: "Математическая формула",
    template: { formula: "", explanation: "" },
  },
  {
    id: "chemical_formula",
    contentType: "chemical_formula",
    label: "Химия",
    hint: "Химическая формула",
    template: { formula: "", explanation: "" },
  },
  {
    id: "musical_notation",
    contentType: "musical_notation",
    label: "Ноты",
    hint: "Нотная запись",
    template: { formula: "", explanation: "" },
  },
];

const blockTypeById = new Map(blockTypes.map((type) => [type.id, type]));
const blockTypeByContentType = new Map(
  blockTypes.map((type) => [type.contentType, type]),
);

export const templates = Object.fromEntries(
  blockTypes.map((type) => [type.id, type.template]),
);

export const allowedImageTypes = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
]);
export const allowedImageExtension = /\.(png|jpe?g|webp|gif)$/i;
export const allowedTextExtension =
  /\.(pdf|docx|pptx|xlsx|md|markdown|html|txt|json|sql|js|jsx|ts|tsx|py|csv)$/i;
const allowedImageDataUrl =
  /^data:image\/(?:png|jpeg|webp|gif);base64,[a-z0-9+/=]+$/i;

export function safeMarkdownUrl(url) {
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

const nextId = () =>
  `content-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const clone = (value) => JSON.parse(JSON.stringify(value));
const isFenceStart = (line) => /^\s*(```|~~~)/.test(line);
const isTableSeparator = (line) =>
  /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
const isTableRow = (line) => line.trim().includes("|") && !isFenceStart(line);
const isStandaloneSeparator = (value) => /^\s*-{2,}\s*$/.test(value);

export function detectType(content) {
  const trimmed = content.trim();
  if (/^```mermaid/i.test(trimmed)) {
    return "mermaid";
  }
  if (/^```/i.test(trimmed) || /^~~~/i.test(trimmed)) {
    return "program_code";
  }
  const lines = trimmed.split("\n");
  if (lines.length > 1 && isTableRow(lines[0]) && isTableSeparator(lines[1])) {
    return "text";
  }
  return "text";
}

function parseCodeFence(content) {
  const match = /^```([^\n`]*)\n([\s\S]*?)\n```\s*$/m.exec(content.trim());
  if (!match) {
    return null;
  }
  return {
    language: match[1]?.trim() || "text",
    code: match[2] || "",
  };
}

function normalizeQuestion(question) {
  if (Array.isArray(question)) {
    return {
      question: typeof question[0] === "string" ? question[0] : "",
      answer: question.slice(1).filter(Boolean).join("\n"),
    };
  }
  if (question && typeof question === "object") {
    const options = Array.isArray(question.options)
      ? question.options.join("\n")
      : question.options;
    const answerParts = [options, question.answer].filter(Boolean);

    return {
      question: typeof question.question === "string" ? question.question : "",
      answer: answerParts.join("\n\n"),
    };
  }
  return { question: typeof question === "string" ? question : "", answer: "" };
}

export function createBlock(templateOrContent, type = "text") {
  const blockType = blockTypeById.get(type) || blockTypes[0];
  const initialData =
    typeof templateOrContent === "string"
      ? markdownToTypedData(templateOrContent, blockType.id)
      : { ...clone(blockType.template), ...(templateOrContent || {}) };

  return normalizeContentBlock(
    {
      content_type: blockType.contentType,
      ai_generated: false,
      ...initialData,
    },
    true,
  );
}

function markdownToTypedData(content, type = detectType(content)) {
  if (type === "program_code") {
    const parsedFence = parseCodeFence(content);
    return parsedFence
      ? { ...parsedFence, explanation: "" }
      : { language: "text", code: content.trim(), explanation: "" };
  }

  if (type === "mermaid") {
    const parsedFence = parseCodeFence(content);
    return {
      title: "Диаграмма",
      md_content: parsedFence?.code || content.trim(),
      explanation: "",
    };
  }

  return { md_content: content.trim() };
}

export function normalizeContentBlock(block, ensureId = false) {
  const source = block && typeof block === "object" ? block : {};
  const contentType = blockTypeByContentType.has(source.content_type)
    ? source.content_type
    : blockTypeById.has(source.type)
      ? blockTypeById.get(source.type).contentType
      : "text";
  const blockType = blockTypeByContentType.get(contentType) || blockTypes[0];
  const normalized = {
    id: source.id || (ensureId ? nextId() : undefined),
    type: blockType.id,
    content_type: blockType.contentType,
    ai_generated:
      typeof source.ai_generated === "boolean" ? source.ai_generated : false,
    ...clone(blockType.template),
  };

  if (contentType === "text") {
    normalized.md_content = String(
      source.md_content ??
        source.content ??
        source.text ??
        source.markdown ??
        "",
    );
  } else if (contentType === "video") {
    normalized.url = String(source.url ?? "");
    normalized.description = String(source.description ?? "");
  } else if (contentType === "image") {
    normalized.image_id = getMediaId(
      source.image_id ?? source.imageId ?? source.image_url ?? source.url ?? "",
    );
  } else if (contentType === "program_code") {
    normalized.language = String(source.language ?? "text");
    normalized.code = String(source.code ?? "");
    normalized.explanation = String(source.explanation ?? "");
  } else if (contentType === "mermaid") {
    normalized.title = String(source.title ?? "Диаграмма");
    normalized.md_content = String(source.md_content ?? source.content ?? "");
    normalized.explanation = String(source.explanation ?? "");
  } else if (contentType === "quiz") {
    const questions = Array.isArray(source.questions)
      ? source.questions
      : source.questions && typeof source.questions === "object"
        ? [source.questions]
        : [];
    normalized.questions = questions.length
      ? questions.map(normalizeQuestion)
      : [{ question: "", answer: "" }];
  } else {
    normalized.formula = String(source.formula ?? "");
    normalized.explanation = String(source.explanation ?? "");
  }

  return normalized;
}

export function normalizeContentBlocks(blocks, fallbackMarkdown = "") {
  if (Array.isArray(blocks) && blocks.length > 0) {
    return blocks.map((block) => normalizeContentBlock(block, true));
  }
  return splitMarkdown(fallbackMarkdown);
}

export function stripUiFields(block) {
  const normalized = normalizeContentBlock(block);
  const payload = {
    content_type: normalized.content_type,
    ai_generated: false,
  };

  if (normalized.content_type === "text") {
    payload.md_content = normalized.md_content;
  } else if (normalized.content_type === "video") {
    payload.url = normalized.url;
    payload.description = normalized.description;
  } else if (normalized.content_type === "image") {
    payload.image_id = normalized.image_id;
  } else if (normalized.content_type === "program_code") {
    payload.language = normalized.language;
    payload.code = normalized.code;
    payload.explanation = normalized.explanation;
  } else if (normalized.content_type === "mermaid") {
    payload.title = normalized.title;
    payload.md_content = normalized.md_content;
    payload.explanation = normalized.explanation;
  } else if (normalized.content_type === "quiz") {
    payload.questions = normalized.questions.map(normalizeQuestion);
  } else {
    payload.formula = normalized.formula;
    payload.explanation = normalized.explanation;
  }

  return payload;
}

export function splitMarkdown(markdown) {
  const source = (markdown || "").trim();
  if (!source) {
    return [createBlock(templates.text, "text")];
  }

  const lines = source.split("\n");
  const blocks = [];
  let buffer = [];

  const flushText = () => {
    const content = buffer.join("\n").trim();
    if (content && !isStandaloneSeparator(content)) {
      blocks.push(createBlock(content, detectType(content)));
    }
    buffer = [];
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];

    if (isFenceStart(line)) {
      flushText();
      const fence = line.trim().slice(0, 3);
      const fenceLines = [line];
      index += 1;
      while (index < lines.length) {
        fenceLines.push(lines[index]);
        if (lines[index].trim().startsWith(fence)) {
          break;
        }
        index += 1;
      }
      const content = fenceLines.join("\n");
      blocks.push(createBlock(content, detectType(content)));
      continue;
    }

    if (!line.trim() || isStandaloneSeparator(line)) {
      flushText();
      continue;
    }

    buffer.push(line);
  }

  flushText();
  return blocks.length > 0 ? blocks : [createBlock(templates.text, "text")];
}

export function blockToMarkdown(block) {
  const normalized = normalizeContentBlock(block);

  if (normalized.content_type === "text") {
    return normalized.md_content.trim();
  }
  if (normalized.content_type === "video") {
    return [
      normalized.url ? `[Видео](${normalized.url})` : "Видео без ссылки",
      normalized.description,
    ]
      .filter(Boolean)
      .join("\n\n");
  }
  if (normalized.content_type === "image") {
    return normalized.image_id ? `Изображение: ${normalized.image_id}` : "";
  }
  if (normalized.content_type === "program_code") {
    return [
      `\`\`\`${normalized.language || "text"}\n${normalized.code}\n\`\`\``,
      normalized.explanation,
    ]
      .filter(Boolean)
      .join("\n\n");
  }
  if (normalized.content_type === "mermaid") {
    return [
      normalized.title ? `### ${normalized.title}` : "",
      `\`\`\`mermaid\n${normalized.md_content}\n\`\`\``,
      normalized.explanation,
    ]
      .filter(Boolean)
      .join("\n\n");
  }
  if (normalized.content_type === "quiz") {
    return normalized.questions
      .map((question, index) =>
        [`${index + 1}. **${question.question || "Вопрос"}**`, question.answer]
          .filter(Boolean)
          .join("\n\n"),
      )
      .join("\n\n");
  }

  return [normalized.formula, normalized.explanation]
    .filter(Boolean)
    .join("\n\n");
}

export function joinBlocks(blocks) {
  return blocks
    .map(blockToMarkdown)
    .map((content) => content.trim())
    .filter((content) => content && !isStandaloneSeparator(content))
    .join("\n\n");
}

export function getBlockTitle(block) {
  const normalized = normalizeContentBlock(block);
  const blockType = blockTypeByContentType.get(normalized.content_type);
  const prefix = blockType?.label || "Блок";

  if (normalized.content_type === "text") {
    return (
      normalized.md_content
        .split("\n")
        .find((line) => line.trim())
        ?.replace(/^#{1,6}\s*/, "")
        .slice(0, 52) || prefix
    );
  }
  if (normalized.content_type === "mermaid") {
    return normalized.title || prefix;
  }
  if (normalized.content_type === "program_code") {
    return `${prefix}${normalized.language ? ` · ${normalized.language}` : ""}`;
  }
  if (normalized.content_type === "quiz") {
    return `${prefix} · ${normalized.questions.length} вопрос(ов)`;
  }
  if (normalized.content_type === "video") {
    return normalized.url || prefix;
  }
  if (normalized.content_type === "image") {
    return normalized.image_id || prefix;
  }
  return normalized.formula || prefix;
}

export function buildAiDraft(lesson, prompt, markdown) {
  const lowerPrompt = prompt.toLowerCase();
  if (lowerPrompt.includes("схем")) {
    return `${markdown}\n\n\`\`\`mermaid\nflowchart TD\n  A[${lesson.title}] --> B[Практика]\n\`\`\``;
  }
  if (lowerPrompt.includes("код")) {
    return `${markdown}\n\n\`\`\`python\n# пример к уроку\n\`\`\``;
  }
  return `${markdown}\n\n> Итог: ${lesson.title} связывает теорию с практическим результатом.`;
}

export const markdownComponents = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    const language = match?.[1]?.toLowerCase();
    const code = String(children).replace(/\n$/, "");

    if (language === "mermaid") {
      return <MermaidDiagram chart={code} />;
    }

    return (
      <SyntaxHighlightedCode className={className} {...props}>
        {children}
      </SyntaxHighlightedCode>
    );
  },
};
