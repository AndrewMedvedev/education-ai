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
  background: "#f6f1e9",
  primaryColor: "#e9dce9",
  primaryTextColor: "#2b2b2b",
  primaryBorderColor: "#8c718c",
  secondaryColor: "#dce8f7",
  tertiaryColor: "#f1e5d8",
  lineColor: "#66778b",
  textColor: "#2b2b2b",
  edgeLabelBackground: "#f6f1e9",
  noteBkgColor: "#f1dfcf",
  noteTextColor: "#654329",
  noteBorderColor: "#c98245",
};

/* -------------------------------------------------------------------------- */
/* Ultimate fallback — всегда валидный SVG, не зависит от Mermaid */
/* -------------------------------------------------------------------------- */
const ULTIMATE_FALLBACK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="100%" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;max-width:100%;display:block;background:#f6f1e9"><rect x="10" y="18" width="120" height="44" rx="8" fill="#e9dce9" stroke="#8c718c" stroke-width="1.5"/><text x="70" y="45" text-anchor="middle" font-family="system-ui,sans-serif" font-size="14" fill="#2b2b2b">Диаграмма</text><path d="M140 40 H180" stroke="#66778b" stroke-width="1.5" fill="none" marker-end="url(#m-arrow)"/><rect x="190" y="18" width="120" height="44" rx="8" fill="#dce8f7" stroke="#8c718c" stroke-width="1.5"/><text x="250" y="45" text-anchor="middle" font-family="system-ui,sans-serif" font-size="13" fill="#2b2b2b">не распознана</text><defs><marker id="m-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#66778b"/></marker></defs></svg>`;

/* -------------------------------------------------------------------------- */
/* Mermaid loader */
/* -------------------------------------------------------------------------- */
const getMermaid = async () => {
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

      return line.replace(/\[([^\]\n]+)\]/g, (match, label) => {
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

  // 3. Убираем все обратные слеши перед кавычками (любое количество)
  result = result.replace(/\\(?:\\\\)*(["'])/g, "$1");

  // 4. Разбиваем склеенные инструкции вида A[Текст]B --> C.
  result = splitStuckFlowchartStatements(result);

  // 5. Mermaid 11 строже парсит спецсимволы внутри [label].
  result = quoteUnsafeSquareLabels(result);

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

  return result.trim();
};

/* -------------------------------------------------------------------------- */
/* Render candidates — ТОЛЬКО исправленная версия */
/* -------------------------------------------------------------------------- */
const createRenderCandidates = (source) => {
  const normalized = normalizeMermaidSource(source);
  const repaired = repairCommonErrors(normalized);
  const candidates = [];

  if (repaired) candidates.push(repaired);
  if (repaired && !hasDiagramType(repaired)) {
    candidates.push(`flowchart TD\n${repaired}`);
  }

  return [...new Set(candidates.filter(Boolean))];
};

/* -------------------------------------------------------------------------- */
/* SVG normalization */
/* -------------------------------------------------------------------------- */
const sanitizeRenderedSvg = (svgElement) => {
  svgElement
    .querySelectorAll("script, foreignObject, iframe, object, embed")
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
    const parsed = parser.parseFromString(svg, "image/svg+xml");
    const svgElement = parsed.documentElement;
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
    const parsed = parser.parseFromString(svg, "image/svg+xml");

    if (parsed.querySelector("parsererror")) {
      return true;
    }

    const svgElement = parsed.documentElement;
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
        svg: ULTIMATE_FALLBACK_SVG,
        error: null,
        recovered: true,
        fallback: true,
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

/* -------------------------------------------------------------------------- */
/* Component */
/* -------------------------------------------------------------------------- */
export default function MermaidDiagram({ chart }) {
  const reactId = useId();
  const renderVersionRef = useRef(0);
  const [svg, setSvg] = useState("");
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState("");

  const normalizedChart = useMemo(() => normalizeMermaidSource(chart), [chart]);

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
        renderMermaid({
          chart: chartToRender,
          componentId,
        }),
      );

      if (cancelled || currentVersion !== renderVersionRef.current) return;

      setSvg(result.svg);
      setErrorMessage(result.error || "");
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
      setStatus("error");
    });

    return () => {
      cancelled = true;
      renderVersionRef.current += 1;
    };
  }, [normalizedChart, componentId]);

  return (
    <div className={["mermaid-diagram", `is-${status}`].join(" ")}>
      {svg ? (
        <div
          className="mermaid-diagram-svg"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : status === "error" ? (
        <div className="mermaid-diagram-error" role="alert">
          <strong>Не удалось отрисовать Mermaid-диаграмму</strong>
          <span>{errorMessage}</span>
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
