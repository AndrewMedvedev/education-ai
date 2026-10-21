import { Fragment } from "react";
import "./content-block-sources.css";

const URL_PATTERN = /https?:\/\/[^\s<>"'«»]+/i;
const TRAILING_PUNCTUATION = /[.,;:!?)\]}]+$/;

// Ссылку открываем только для http(s): javascript:, data: и прочие схемы не делаем кликабельными.
function toSafeHref(value) {
  const raw = String(value || "")
    .trim()
    .replace(TRAILING_PUNCTUATION, "");
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return url.protocol === "http:" || url.protocol === "https:"
      ? url.href
      : null;
  } catch {
    return null;
  }
}

function shortLabel(href) {
  try {
    const url = new URL(href);
    const path = url.pathname === "/" ? "" : url.pathname;
    const label = `${url.hostname.replace(/^www\./, "")}${path}`;
    return label.length > 80 ? `${label.slice(0, 77)}…` : label;
  } catch {
    return href;
  }
}

/**
 * Источники блока с backend: list[str]. Строка может быть ссылкой, текстом
 * со ссылкой внутри («Название — https://…») или просто текстом.
 */
export function normalizeSources(sources) {
  if (!Array.isArray(sources)) return [];
  return sources
    .map((item) => {
      if (item && typeof item === "object") {
        const href = toSafeHref(item.url || item.href || item.link);
        const label = String(item.title || item.name || "").trim();
        if (!href && !label) return null;
        return { href, label: label || (href ? shortLabel(href) : "") };
      }
      const text = String(item ?? "").trim();
      if (!text) return null;
      // «javascript:…», «data:…» и т.п. не показываем вовсе.
      if (/^[a-z][a-z0-9+.-]*:/i.test(text) && !/^https?:/i.test(text)) {
        return null;
      }
      const match = text.match(URL_PATTERN);
      const href = match ? toSafeHref(match[0]) : null;
      if (!href) return { href: null, label: text };
      const rest = text
        .replace(match[0], "")
        .replace(/^[\s—–\-:|]+|[\s—–\-:|]+$/g, "")
        .trim();
      return { href, label: rest || shortLabel(href) };
    })
    .filter(Boolean);
}

export function hasSources(sources) {
  return normalizeSources(sources).length > 0;
}

export default function ContentBlockSources({ sources, className = "" }) {
  const items = normalizeSources(sources);
  if (items.length === 0) return null;

  return (
    <aside
      className={`content-block-sources ${className}`.trim()}
      aria-label="Источники"
    >
      <span className="content-block-sources-title">Источники</span>
      <ol>
        {items.map((item, index) => (
          <li key={`${item.href || item.label}-${index}`}>
            {item.href ? (
              <a
                href={item.href}
                target="_blank"
                rel="noopener noreferrer nofollow"
                referrerPolicy="no-referrer"
                title={item.href}
              >
                {item.label}
              </a>
            ) : (
              <Fragment>{item.label}</Fragment>
            )}
          </li>
        ))}
      </ol>
    </aside>
  );
}
