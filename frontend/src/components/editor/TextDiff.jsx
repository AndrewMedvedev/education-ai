// Пословное сравнение «было → стало» для окна подтверждения сохранения.
// Показывает только изменённые места с небольшим контекстом вокруг.

const MAX_LCS_CELLS = 400_000;
const CONTEXT_CHARS = 60;

function tokenize(text) {
  return String(text ?? "").match(/\s+|[^\s]+/g) || [];
}

function pushSegment(segments, type, text) {
  if (!text) return;
  const last = segments[segments.length - 1];
  if (last && last.type === type) last.text += text;
  else segments.push({ type, text });
}

/** [{ type: "eq" | "del" | "ins", text }] */
export function diffText(before, after) {
  const a = tokenize(before);
  const b = tokenize(after);
  let start = 0;
  while (start < a.length && start < b.length && a[start] === b[start]) {
    start += 1;
  }
  let endA = a.length;
  let endB = b.length;
  while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) {
    endA -= 1;
    endB -= 1;
  }

  const segments = [];
  pushSegment(segments, "eq", a.slice(0, start).join(""));
  const midA = a.slice(start, endA);
  const midB = b.slice(start, endB);

  if (midA.length * midB.length > MAX_LCS_CELLS) {
    pushSegment(segments, "del", midA.join(""));
    pushSegment(segments, "ins", midB.join(""));
  } else {
    // LCS по словам для середины, где тексты отличаются.
    const rows = midA.length + 1;
    const cols = midB.length + 1;
    const table = new Uint32Array(rows * cols);
    for (let i = midA.length - 1; i >= 0; i -= 1) {
      for (let j = midB.length - 1; j >= 0; j -= 1) {
        table[i * cols + j] =
          midA[i] === midB[j]
            ? table[(i + 1) * cols + j + 1] + 1
            : Math.max(table[(i + 1) * cols + j], table[i * cols + j + 1]);
      }
    }
    let i = 0;
    let j = 0;
    while (i < midA.length && j < midB.length) {
      if (midA[i] === midB[j]) {
        pushSegment(segments, "eq", midA[i]);
        i += 1;
        j += 1;
      } else if (table[(i + 1) * cols + j] >= table[i * cols + j + 1]) {
        pushSegment(segments, "del", midA[i]);
        i += 1;
      } else {
        pushSegment(segments, "ins", midB[j]);
        j += 1;
      }
    }
    pushSegment(segments, "del", midA.slice(i).join(""));
    pushSegment(segments, "ins", midB.slice(j).join(""));
  }

  pushSegment(segments, "eq", a.slice(endA).join(""));
  return segments;
}

function trimContext(text, position) {
  const value = text.replace(/\s+/g, " ");
  if (value.length <= CONTEXT_CHARS * 2) return value;
  if (position === "start") return `…${value.slice(-CONTEXT_CHARS)}`;
  if (position === "end") return `${value.slice(0, CONTEXT_CHARS)}…`;
  return `${value.slice(0, CONTEXT_CHARS)} … ${value.slice(-CONTEXT_CHARS)}`;
}

/** Компактный показ различий двух текстов. */
export default function TextDiff({ before, after }) {
  const segments = diffText(before, after);
  const hasChanges = segments.some((segment) => segment.type !== "eq");
  if (!hasChanges)
    return <span className="app-text-diff-empty">без изменений</span>;

  return (
    <span className="app-text-diff">
      {segments.map((segment, index) => {
        if (segment.type === "del") {
          return (
            <del key={index} title="Удалено">
              {segment.text.trim() ? segment.text : "⏎"}
            </del>
          );
        }
        if (segment.type === "ins") {
          return (
            <ins key={index} title="Добавлено">
              {segment.text.trim() ? segment.text : "⏎"}
            </ins>
          );
        }
        const position =
          index === 0
            ? "start"
            : index === segments.length - 1
              ? "end"
              : "middle";
        return <span key={index}>{trimContext(segment.text, position)}</span>;
      })}
    </span>
  );
}
