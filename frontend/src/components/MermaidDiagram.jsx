"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

/* -------------------------------------------------------------------------- */
/* Global Mermaid */
/* -------------------------------------------------------------------------- */
let mermaidPromise = null;
let mermaidInitialized = false;
let globalRenderCounter = 0;

let renderQueue = Promise.resolve();
const enqueueRender = (task) => {
  const result = renderQueue.then(task, task);
  renderQueue = result.catch(() => undefined);
  return result;
};

const formatMermaidError = (error) => {
  const rawMessage =
    error?.str || error?.message || error?.hash?.text || String(error ?? "");
  const message = String(rawMessage).replace(/\s+/g, " ").trim();

  if (!message) {
    return "Mermaid не смог обработать код диаграммы.";
  }

  return message.length > 280 ? `${message.slice(0, 277)}...` : message;
};

/* -------------------------------------------------------------------------- */
/* Theme */
/* -------------------------------------------------------------------------- */
const themeVariables = {
  background: "#ffffff",
  primaryColor: "#dbeafe",
  primaryTextColor: "#172033",
  primaryBorderColor: "#3466ca",
  secondaryColor: "#e0f2fe",
  tertiaryColor: "#eef2ff",
  lineColor: "#3466ca",
  textColor: "#172033",
  edgeLabelBackground: "#ffffff",
  noteBkgColor: "#eff6ff",
  noteTextColor: "#1e3a5f",
  noteBorderColor: "#60a5fa",
  fontFamily: '"Manrope", Arial, sans-serif',
};

/* -------------------------------------------------------------------------- */
/* Ultimate fallback — всегда валидный SVG, не зависит от Mermaid */
/* -------------------------------------------------------------------------- */
const ULTIMATE_FALLBACK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="100%" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;max-width:100%;display:block;background:#ffffff"><rect x="10" y="18" width="120" height="44" rx="8" fill="#dbeafe" stroke="#3466ca" stroke-width="1.5"/><text x="70" y="45" text-anchor="middle" font-family="system-ui,sans-serif" font-size="14" fill="#172033">Диаграмма</text><path d="M140 40 H180" stroke="#49627f" stroke-width="1.5" fill="none" marker-end="url(#m-arrow)"/><rect x="190" y="18" width="120" height="44" rx="8" fill="#e0f2fe" stroke="#3466ca" stroke-width="1.5"/><text x="250" y="45" text-anchor="middle" font-family="system-ui,sans-serif" font-size="13" fill="#172033">не распознана</text><defs><marker id="m-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#49627f"/></marker></defs></svg>`;

/* -------------------------------------------------------------------------- */
/* Mermaid loader */
/* -------------------------------------------------------------------------- */
const getMermaid = async () => {
  if (typeof document !== "undefined" && document.fonts?.ready) {
    await document.fonts.ready;
  }
  if (!mermaidPromise) {
    mermaidPromise = import("mermaid").then(
      (module) => module.default ?? module,
    );
  }
  const mermaid = await mermaidPromise;
  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      suppressErrorRendering: true,
      theme: "base",
      themeVariables,
      flowchart: {
        htmlLabels: false,
        useMaxWidth: true,
        nodeSpacing: 30,
        rankSpacing: 35,
        curve: "linear",
      },
      sequence: {
        useMaxWidth: true,
        diagramMarginX: 20,
        diagramMarginY: 20,
        actorMargin: 40,
        width: 120,
        height: 50,
        boxMargin: 8,
        messageMargin: 25,
      },
      gantt: {
        useMaxWidth: true,
      },
    });
    mermaidInitialized = true;
  }
  return mermaid;
};

/* -------------------------------------------------------------------------- */
/* Source helpers */
/* -------------------------------------------------------------------------- */
const normalizeTypography = (source) =>
  String(source ?? "")
    .replace(/\r\n?/g, "\n")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .replace(/\u00A0/g, " ")
    .replace(/[\u2018\u2019\u2032]/g, "'")
    .replace(/[\u201C\u201D\u2033]/g, '"')
    .replace(/[\u2013\u2014]/g, "-")
    .trim();

const stripCodeFence = (source) => {
  const value = String(source ?? "").trim();
  const normalFence = value.match(
    /^```(?:mermaid)?[^\S\r\n]*\r?\n([\s\S]*?)\r?\n```$/i,
  );
  if (normalFence) return normalFence[1].trim();
  return value
    .replace(/^```(?:mermaid)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();
};

/* Удаляем init-директивы ПО ВСЕМУ ТЕКСТУ */
const stripInitDirectives = (source) =>
  String(source ?? "")
    .replace(/\s*%%\{\{?\s*(?:init|initialize)\s*:[\s\S]*?\}\}?\s*%%\s*/gim, "")
    .trim();

const normalizeMermaidSource = (source) => {
  const normalized = normalizeTypography(source);
  const withoutFence = stripCodeFence(normalized);
  return stripInitDirectives(withoutFence).trim();
};

/* -------------------------------------------------------------------------- */
/* Diagram detection */
/* -------------------------------------------------------------------------- */
const DIAGRAM_TYPE_PATTERN =
  /^\s*(flowchart|graph|sequenceDiagram|classDiagram(?:-v2)?|stateDiagram(?:-v2)?|erDiagram|journey|gantt|pie|gitGraph|mindmap|timeline|quadrantChart|requirementDiagram|C4Context|C4Container|C4Component|C4Dynamic|sankey-beta|block-beta|xychart-beta|zenuml|architecture-beta|packet-beta|kanban)\b/i;

const hasDiagramType = (source) =>
  DIAGRAM_TYPE_PATTERN.test(String(source ?? "").trim());

const quoteUnsafeSquareLabels = (source) =>
  String(source ?? "")
    .split("\n")
    .map((line) => {
      if (/^\s*subgraph\s+[A-Za-z_][\w-]*\s+\[[^\]]+\]\s*$/i.test(line)) {
        return line;
      }

      return line.replace(/(?<!\[)\[(?!\[)([^\]\n]+)\](?!\])/g, (match, label) => {
        const trimmed = label.trim();

        if (!trimmed || /^["'`]/.test(trimmed)) {
          return match;
        }

        if (/^[A-Za-z0-9_. -]+$/.test(trimmed)) {
          return match;
        }

        return `["${trimmed.replace(/"/g, "#quot;")}"]`;
      });
    })
    .join("\n");

const stripInlineComments = (source) =>
  String(source ?? "")
    .split("\n")
    .map((line) => {
      if (/^\s*%%/.test(line)) return line;
      return line.replace(/\s+%%.*$/, "");
    })
    .join("\n");

const splitStuckFlowchartStatements = (source) =>
  String(source ?? "")
    // A["Текст"]"direction TB -> A["Текст"]\ndirection TB
    .replace(/\]\s*["']\s*(?=direction\b)/gi, "]\n")
    // A["Текст"]"node[Текст] -> A["Текст"]\nnode[Текст]
    .replace(/\]\s*["']\s*(?=[A-Za-z_][\w-]*\s*[\[({])/g, "]\n")
    // direction TBnode[Текст] -> direction TB\nnode[Текст]
    .replace(/\bdirection\s+(TB|TD|BT|RL|LR)(?=[A-Za-z_])/gi, "direction $1\n")
    // A[Текст]B --> C / A["Текст"]B --> C
    .replace(
      /(\])([A-Za-z_][\w-]*\s*(?=(?:[-=.]{1,3}[->.]|-->|---|==>|\.\.)))/g,
      "$1\n$2",
    )
    // A[Текст]B[Другой текст] / A["Текст"]B["Другой текст"]
    .replace(/(\])([A-Za-z_][\w-]*\s*(?=[\[({]))/g, "$1\n$2")
    // A[Текст]end / A["Текст"]"end -> A[Текст]\nend
    .replace(/([\]\)])\s*["']?\s*(?=end\b)/gi, "$1\n")
    // endA[Текст] -> end\nA[Текст]
    .replace(/\bend(?=[A-Za-z_][\w-]*\s*[\[({])/gi, "end\n")
    // subgraph Id[Название] -> subgraph Id [Название]
    .replace(/((?:^|\n)\s*subgraph\s+[A-Za-z_][\w-]*)(?=\s*\[)/g, "$1 ")
    // subgraph "Название"direction TB / subgraph "Название"node[Текст]
    .replace(
      /((?:^|\n)\s*subgraph\s+["'][^"'\n]+["'])(\s*(?:direction\b|[A-Za-z_][\w-]*\s*(?=[\[({])))/g,
      "$1\n$2",
    );

/* LLM-SLIPS-START */
/* -------------------------------------------------------------------------- */
/* Типовые огрехи сгенерированных flowchart-схем                               */
/* -------------------------------------------------------------------------- */
const FLOWCHART_PATTERN = /^\s*(flowchart|graph)\b/i;

// Допустимые пары скобок у фигур узла: открывающая -> закрывающая.
const NODE_SHAPE_CLOSERS = {
  "[": "]",
  "(": ")",
  "{": "}",
  "[[": "]]",
  "((": "))",
  "([": "])",
  "[(": ")]",
  "{{": "}}",
  "(((": ")))",
};

const UNSAFE_EDGE_LABEL = /[()[\]{}"'<>#;:&]/;

const repairFlowchartSlips = (source) => {
  const text = String(source ?? "");
  // Правки ниже специфичны для flowchart; sequence/class/state диаграммы не трогаем.
  const firstLine = text.split("\n").find((line) => line.trim() && !/^\s*%%/.test(line)) ?? "";
  if (hasDiagramType(firstLine) && !FLOWCHART_PATTERN.test(firstLine)) return text;

  return text
    .split("\n")
    // `% комментарий` с одним процентом и несуществующая директива classId ломают парсер.
    .filter((line) => !/^\s*%(?!%)/.test(line) && !/^\s*classId\b/i.test(line))
    // `class a,b,c` без имени класса: список узлов есть, а применять нечего.
    .filter((line) => !/^\s*class\s+\S+\s*;?\s*$/.test(line))
    .map((line) => {
      if (/^\s*%%/.test(line)) return line;
      let next = line;

      // classDef/style: свойства разделяются запятыми, `;` внутри обрывает инструкцию.
      if (/^\s*(classDef|style|linkStyle)\b/.test(next)) {
        // `shape:` не является CSS-свойством и не поддерживается в classDef.
        next = next.replace(/[;,]\s*shape\s*:\s*[\w-]+/gi, "");
        return next.replace(/;(?=\s*\S)/g, ",");
      }

      // subgraph ID [ Заголовок: с двоеточием ] -> subgraph ID ["Заголовок: с двоеточием"]
      next = next.replace(
        /^(\s*subgraph\s+[A-Za-z_][\w-]*)\s*\[\s*([^\]"\n]+?)\s*\]\s*$/,
        (match, head, title) => `${head}["${title.replace(/"/g, "#quot;")}"]`,
      );

      // `==>>` и `-->>` в flowchart не существуют; `||метка|` — лишняя вертикальная черта.
      next = next.replace(/(==|--)>>(?=\s*\||\s)/g, "$1>");
      next = next.replace(/((?:==+|--+|-\.+-)>?)\s*\|\|\s*([^|\n]*?)\s*\|/g, "$1|$2|");

      // Подпись связи со спецсимволами: |230 В (падение U)| -> |"230 В (падение U)"|
      next = next.replace(
        /((?:<?(?:==+|--+|-\.+-)[>ox]?))\s*\|([^|\n]+?)\|/g,
        (match, arrow, label) => {
          const trimmed = label.trim();
          if (!trimmed || /^".*"$/.test(trimmed) || !UNSAFE_EDGE_LABEL.test(trimmed)) return match;
          return `${arrow}|"${trimmed.replace(/"/g, "#quot;")}"|`;
        },
      );

      // Узел с подписью в кавычках и несовпавшими скобками: A("текст"] / A["текст"]] / A({{"текст"}})
      next = next.replace(
        /([A-Za-z_][\w-]*)([[({]{1,3})("[^"\n]*")([\])}]{1,3})/g,
        (match, id, open, label, close) => {
          const expected = NODE_SHAPE_CLOSERS[open];
          if (expected) return expected === close ? match : `${id}${open}${label}${expected}`;
          const fallback = open.includes("{{") ? "{{" : open.includes("{") ? "{" : open.includes("(") ? "(" : "[";
          return `${id}${fallback}${label}${NODE_SHAPE_CLOSERS[fallback]}`;
        },
      );

      // Лишняя кавычка после закрывающей скобки в конце строки: Q{"Текст?"}"
      next = next.replace(/([\])}])"(\s*;?\s*)$/, "$1$2");

      return next;
    })
    .join("\n");
};
/* LLM-SLIPS-END */

/* -------------------------------------------------------------------------- */
/* УЛУЧШЕННЫЙ ремонт — удаляем все обратные слеши, вставляем пробелы между узлами */
/* -------------------------------------------------------------------------- */
const repairCommonErrors = (source) => {
  let result = String(source ?? "").trim();
  if (!result) return "";

  // 1. Удаляем init-директивы
  result = stripInitDirectives(result);

  // 2. Mermaid поддерживает комментарии отдельной строкой, но inline `%%` часто ломают парсер.
  result = stripInlineComments(result);

  // 2a. Огрехи генерации в flowchart: несовпавшие скобки, лишние кавычки, битые стрелки.
  result = repairFlowchartSlips(result);

  // Escaped quotes are label content, not Mermaid delimiters.
  result = result.replace(/\\"/g, "#quot;");
  result = result.replace(/\\'/g, "#apos;");

  // Mermaid reserves `end`; keep subgraph terminators but rename node ids.
  result = result.replace(/\bend(?=\s*[\[({])/gi, "node_end");
  result = result.replace(/(-->\s*)end\b/gi, "$1node_end");

  // 4. Разбиваем склеенные инструкции вида A[Текст]B --> C.
  result = splitStuckFlowchartStatements(result);

  // 5. Mermaid 11 строже парсит спецсимволы внутри [label].
  result = result.replace(/([A-Za-z_][\w-]*)(\[\[|\(\()([^\]\)\n]+)(\]\]|\)\))/g,
    (match, id, open, label, close) => {
      if ((open === "[[") !== (close === "]]")) return match;
      const trimmed = label.trim();
      if (/^".*"$/.test(trimmed)) return match;
      return `${id}${open}"${trimmed.replace(/"/g, "#quot;")}"${close}`;
    });
  result = quoteUnsafeSquareLabels(result);
  result = result.replace(/([A-Za-z_][\w-]*)(\{\{|\{)([^{}\n]+)(\}\}|\})/g,
    (match, id, open, label, close) => {
      if ((open === "{{") !== (close === "}}")) return match;
      const trimmed = label.trim();
      if (!trimmed || /^".*"$/.test(trimmed)) return match;
      if (/^[A-Za-z0-9_. -]+$/.test(trimmed)) return match;
      return `${id}${open}"${trimmed.replace(/"/g, "#quot;")}"${close}`;
    });

  // 6. Повторяем после закавычивания, потому что строка могла стать A["Текст"]B --> C.
  result = splitStuckFlowchartStatements(result);
  result = result.replace(/([\]\)])([A-Za-z_])/g, "$1 $2");

  // 7. Оборачиваем простой текстовый subgraph в кавычки, не трогая форму `subgraph id [label]`.
  result = result.replace(
    /subgraph\s+([^\s"'\n][^\n]*?)(\s*\n)/g,
    (match, title, rest) => {
      if (/^["']/.test(title) || /\[[^\]]+\]\s*$/.test(title)) return match;
      return `subgraph "${title}"${rest}`;
    },
  );

  // 8. Удаляем лишние пустые строки и пробелы в начале строк
  result = result.replace(/\n\s*\n/g, "\n");
  result = result.replace(/^[ \t]+/gm, "");

  // Links and callbacks are disabled by securityLevel=strict; malformed
  // legacy click lines must not invalidate the entire diagram.
  result = result.split("\n").filter((line) => !/^\s*click\s+/i.test(line)).join("\n");

  return result.trim();
};

/* -------------------------------------------------------------------------- */
/* Render candidates — ТОЛЬКО исправленная версия */
/* -------------------------------------------------------------------------- */
export const createRenderCandidates = (source) => {
  const normalized = normalizeMermaidSource(source);
  const repaired = repairCommonErrors(normalized);
  const candidates = [];

  if (repaired) candidates.push(repaired);
  if (repaired && !hasDiagramType(repaired)) {
    candidates.push(`flowchart TD\n${repaired}`);
  }

  return [...new Set(candidates.filter(Boolean))];
};

export const validateMermaidSource = async (chart) => {
  const candidates = createRenderCandidates(chart);
  if (!candidates.length) throw new Error("Код Mermaid пустой.");
  const mermaid = await getMermaid();
  return enqueueRender(async () => {
    let lastError;
    for (const candidate of candidates) {
      try {
        await validateCandidate(mermaid, candidate);
        return candidate;
      } catch (error) {
        lastError = error;
      }
    }
    const line = lastError?.hash?.loc?.first_line ?? lastError?.hash?.line;
    throw new Error(`Mermaid${line ? `, строка ${line}` : ""}: ${formatMermaidError(lastError)}`);
  });
};

/* -------------------------------------------------------------------------- */
/* SVG normalization */
/* -------------------------------------------------------------------------- */
const sanitizeRenderedSvg = (svgElement) => {
  svgElement
    .querySelectorAll("script, iframe, object, embed")
    .forEach((element) => element.remove());

  svgElement.querySelectorAll("*").forEach((element) => {
    [...element.attributes].forEach((attribute) => {
      const name = attribute.name.toLowerCase();
      const value = attribute.value.trim();

      if (name.startsWith("on")) {
        element.removeAttribute(attribute.name);
        return;
      }

      if (
        (name === "href" || name.endsWith(":href")) &&
        /^javascript:/i.test(value)
      ) {
        element.removeAttribute(attribute.name);
      }
    });
  });
};

const normalizeRenderedSvg = (svg) => {
  if (!svg) return "";
  try {
    const parser = new DOMParser();
    const xmlSafeSvg = svg.replace(/<br\s*\/?>/gi, "<br/>");
    const parsed = parser.parseFromString(xmlSafeSvg, "image/svg+xml");
    const svgElement = parsed.querySelector("parsererror")
      ? parser.parseFromString(svg, "text/html").querySelector("svg")
      : parsed.documentElement;
    if (!svgElement || svgElement.nodeName.toLowerCase() !== "svg") {
      return svg;
    }

    sanitizeRenderedSvg(svgElement);
    svgElement.removeAttribute("width");
    svgElement.removeAttribute("height");
    svgElement.setAttribute("width", "100%");
    svgElement.setAttribute("preserveAspectRatio", "xMidYMid meet");

    const currentStyle = svgElement.getAttribute("style") ?? "";
    const cleanStyle = currentStyle
      .replace(/(?:^|;)\s*max-width\s*:[^;]*/gi, "")
      .replace(/(?:^|;)\s*width\s*:[^;]*/gi, "")
      .replace(/(?:^|;)\s*height\s*:[^;]*/gi, "");

    svgElement.setAttribute(
      "style",
      [
        cleanStyle,
        "width:100%",
        "height:auto",
        "max-width:100%",
        "display:block",
      ]
        .filter(Boolean)
        .join(";"),
    );

    return new XMLSerializer().serializeToString(svgElement);
  } catch {
    return svg;
  }
};

/* -------------------------------------------------------------------------- */
/* Проверка на ошибки — только явные индикаторы */
/* -------------------------------------------------------------------------- */
const isErrorSvg = (svg) => {
  if (!svg) return true;

  try {
    const parser = new DOMParser();
    const parsed = parser.parseFromString(svg.replace(/<br\s*\/?>/gi, "<br/>"), "image/svg+xml");
    const svgElement = parsed.querySelector("parsererror")
      ? parser.parseFromString(svg, "text/html").querySelector("svg")
      : parsed.documentElement;
    if (!svgElement || svgElement.nodeName.toLowerCase() !== "svg") {
      return true;
    }

    const rootClass = svgElement.getAttribute("class") || "";
    const roleDescription =
      svgElement.getAttribute("aria-roledescription") || "";
    const visibleText = svgElement.textContent || "";

    return (
      /\berror\b/i.test(rootClass) ||
      /\berror\b/i.test(roleDescription) ||
      /\b(?:syntax|parse|lexical) error\b/i.test(visibleText)
    );
  } catch {
    return false;
  }
};

/* -------------------------------------------------------------------------- */
/* DOM cleanup */
/* -------------------------------------------------------------------------- */
const escapeSelectorValue = (value) =>
  typeof CSS !== "undefined" && typeof CSS.escape === "function"
    ? CSS.escape(value)
    : String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");

const cleanupMermaidDom = (id) => {
  if (typeof document === "undefined" || !id) return;

  [id, `d${id}`, `i${id}`].forEach((elementId) => {
    document.getElementById(elementId)?.remove();
  });

  const escapedId = escapeSelectorValue(id);
  document
    .querySelectorAll(`[id^="${escapedId}"], [id^="d${escapedId}"]`)
    .forEach((element) => {
      if (!element.closest(".mermaid-diagram")) {
        element.remove();
      }
    });
};

/* -------------------------------------------------------------------------- */
/* Render single candidate */
/* -------------------------------------------------------------------------- */
const validateCandidate = async (mermaid, source) => {
  if (typeof mermaid.parse !== "function") return;

  await mermaid.parse(source, { suppressErrors: false });
};

const renderCandidate = async (mermaid, source, id) => {
  try {
    await validateCandidate(mermaid, source);

    const result = await mermaid.render(id, source);
    if (!result?.svg) {
      return {
        svg: null,
        error: "Mermaid вернул пустой SVG для этой диаграммы.",
      };
    }
    if (isErrorSvg(result.svg)) {
      return {
        svg: null,
        error: "Mermaid вернул SVG с ошибкой парсинга диаграммы.",
      };
    }
    return { svg: normalizeRenderedSvg(result.svg), error: null };
  } catch (error) {
    return { svg: null, error: formatMermaidError(error) };
  } finally {
    cleanupMermaidDom(id);
  }
};

/* -------------------------------------------------------------------------- */
/* Complete Mermaid render — если не удалось, возвращаем ultimate fallback */
/* -------------------------------------------------------------------------- */
const renderMermaid = async ({ chart, componentId }) => {
  let lastError = "Не удалось отрисовать Mermaid-диаграмму.";

  try {
    const mermaid = await getMermaid();
    const candidates = createRenderCandidates(chart);

    if (!candidates.length) {
      return {
        svg: "",
        error: "Код диаграммы пустой.",
        recovered: false,
        fallback: false,
      };
    }

    for (let index = 0; index < candidates.length; index += 1) {
      const source = candidates[index];
      const id = `m-${componentId}-${Date.now()}-${globalRenderCounter++}-${index}`;
      const safeId = id.replace(/^[^a-zA-Z]+/, "m");

      const result = await renderCandidate(mermaid, source, safeId);
      if (result.svg) {
        return {
          svg: result.svg,
          error: null,
          recovered: index > 0,
          fallback: false,
        };
      }
      if (result.error) {
        lastError = result.error;
      }
    }
  } catch (error) {
    lastError = formatMermaidError(error);
  }

  return {
    svg: "",
    error: lastError,
    recovered: false,
    fallback: false,
  };
};

export const auditMermaidRender = (chart, componentId) =>
  enqueueRender(() => renderMermaid({ chart, componentId }));

/* -------------------------------------------------------------------------- */
/* Component */
/* -------------------------------------------------------------------------- */
export default function MermaidDiagram({ chart, onRendered, lessonId, blockId }) {
  const reactId = useId();
  const svgHostRef = useRef(null);
  const renderVersionRef = useRef(0);
  const [svg, setSvg] = useState("");
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [showSource, setShowSource] = useState(false);

  const normalizedChart = useMemo(() => normalizeMermaidSource(chart), [chart]);

  useEffect(() => {
    if (svg && onRendered) onRendered(svgHostRef.current?.querySelector("svg") ?? null);
  }, [svg, onRendered]);

  const componentId = useMemo(() => {
    const safeId = String(reactId)
      .replace(/[^a-zA-Z0-9_-]/g, "")
      .toLowerCase();
    const base = safeId || `diagram-${globalRenderCounter++}`;
    return base.replace(/^[^a-zA-Z]+/, "m");
  }, [reactId]);

  useEffect(() => {
    const chartToRender =
      normalizedChart || "flowchart TD\n  A[Пустая диаграмма]";
    const currentVersion = ++renderVersionRef.current;
    let cancelled = false;

    setStatus("loading");
    setSvg("");
    setErrorMessage("");

    const execute = async () => {
      const result = await enqueueRender(() =>
        cancelled ? null : renderMermaid({ chart: chartToRender, componentId }),
      );

      if (!result || cancelled || currentVersion !== renderVersionRef.current) return;

      setSvg(result.svg);
      setErrorMessage(result.error || "");
      if (result.error) {
        const detail = { lessonId, blockId, source: normalizedChart, error: result.error };
        console.error("Mermaid render failed", detail);
        window.dispatchEvent(new CustomEvent("mermaid:render-error", { detail }));
      }
      if (result.error) {
        setStatus("error");
      } else if (result.fallback) {
        setStatus("fallback");
      } else if (result.recovered) {
        setStatus("recovered");
      } else {
        setStatus("ready");
      }
    };

    execute().catch((error) => {
      if (cancelled || currentVersion !== renderVersionRef.current) return;
      setSvg("");
      setErrorMessage(formatMermaidError(error));
      const detail = { lessonId, blockId, source: normalizedChart, error: formatMermaidError(error) };
      console.error("Mermaid render failed", detail);
      window.dispatchEvent(new CustomEvent("mermaid:render-error", { detail }));
      setStatus("error");
    });

    return () => {
      cancelled = true;
      renderVersionRef.current += 1;
    };
  }, [normalizedChart, componentId, retryCount, lessonId, blockId]);

  return (
    <div className={["mermaid-diagram", `is-${status}`].join(" ")}>
      {svg ? (
        <div
          ref={svgHostRef}
          className="mermaid-diagram-svg"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : status === "error" ? (
        <div className="mermaid-diagram-error" role="alert">
          <strong>Схему пока не удалось показать</strong>
          <span>{errorMessage}</span>
          <div className="mermaid-diagram-error-actions">
            <button type="button" onClick={() => setRetryCount((count) => count + 1)}>Повторить отрисовку</button>
            <button type="button" onClick={() => setShowSource((shown) => !shown)} aria-expanded={showSource}>
              {showSource ? "Скрыть исходный код" : "Показать исходный код"}
            </button>
          </div>
          {showSource && <pre className="mermaid-diagram-source">{normalizedChart}</pre>}
        </div>
      ) : (
        <div
          className="mermaid-diagram-placeholder"
          role="status"
          aria-live="polite"
        >
          <strong>Схема Mermaid загружается</strong>
          <span>Подготавливаем визуализацию.</span>
        </div>
      )}
    </div>
  );
}
