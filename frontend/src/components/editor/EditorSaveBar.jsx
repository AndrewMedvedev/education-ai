import { useEffect, useMemo, useState } from "react";
import ConfirmDialog from "../ui/ConfirmDialog";
import TextDiff from "./TextDiff";
import {
  isDerivedDraftField,
  useEditorDraftStore,
} from "../../stores/editorDraftStore";

const FIELD_LABELS = {
  title: "Название",
  description: "Описание",
  summary: "Краткое описание",
  duration: "Длительность",
  learningObjectives: "Цели обучения",
  learning_objectives: "Цели обучения",
  contentBlocks: "Содержимое урока",
  estimatedTimeMinutes: "Длительность, мин",
  order: "Порядок",
};

const KIND_LABELS = { module: "Модуль", lesson: "Урок" };

function shorten(value, limit = 140) {
  const text = String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) return "пусто";
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function pluralBlocks(count) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "блок";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "блока";
  return "блоков";
}

const BLOCK_TYPE_LABELS = {
  text: "текст",
  video: "видео",
  image: "изображение",
  program_code: "код",
  mermaid: "диаграмма",
  quiz: "вопросы",
  math: "формула",
  chemical: "формула",
  musical: "ноты",
};

function blockText(block) {
  if (!block || typeof block !== "object") return String(block ?? "");
  const parts = [
    block.title,
    block.md_content,
    block.code,
    block.formula,
    block.url,
    block.description,
    block.explanation,
  ];
  if (Array.isArray(block.questions)) {
    block.questions.forEach((question) => {
      parts.push(question?.question, question?.answer);
    });
  }
  if (block.image_id) parts.push(`[изображение ${block.image_id}]`);
  return parts
    .filter((part) => part !== undefined && part !== null && part !== "")
    .map(String)
    .join("\n");
}

function blockLabel(block, index) {
  const type = BLOCK_TYPE_LABELS[block?.content_type] || "блок";
  return `Блок ${index + 1} (${type})`;
}

function textValue(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item ?? "").trim())
      .filter(Boolean)
      .join("\n");
  }
  return String(value ?? "");
}

/** Что именно поменялось в блоках урока: изменённые, добавленные и удалённые блоки. */
function ContentBlocksChange({ before, after }) {
  const next = Array.isArray(after) ? after : [];
  const prev = Array.isArray(before) ? before : null;
  if (!prev) {
    return (
      <div className="app-changes-diff">
        <ins>
          изменено содержимое ({next.length} {pluralBlocks(next.length)})
        </ins>
      </div>
    );
  }

  const rows = [];
  const total = Math.max(prev.length, next.length);
  for (let index = 0; index < total; index += 1) {
    const oldText = index < prev.length ? blockText(prev[index]) : null;
    const newText = index < next.length ? blockText(next[index]) : null;
    if (oldText === newText) continue;
    if (oldText === null) {
      rows.push({
        index,
        kind: "added",
        label: blockLabel(next[index], index),
        newText,
      });
    } else if (newText === null) {
      rows.push({
        index,
        kind: "removed",
        label: blockLabel(prev[index], index),
        oldText,
      });
    } else {
      rows.push({
        index,
        kind: "changed",
        label: blockLabel(next[index], index),
        oldText,
        newText,
      });
    }
  }

  if (!rows.length) {
    return (
      <div className="app-changes-diff">
        <ins>изменены параметры блоков</ins>
      </div>
    );
  }

  const visible = rows.slice(0, 6);
  return (
    <ul className="app-changes-blocks">
      {visible.map((row) => (
        <li key={`${row.kind}-${row.index}`}>
          <strong>
            {row.label}
            {row.kind === "added"
              ? " — новый"
              : row.kind === "removed"
                ? " — удалён"
                : ""}
          </strong>
          {row.kind === "changed" ? (
            <TextDiff before={row.oldText} after={row.newText} />
          ) : row.kind === "added" ? (
            <span className="app-text-diff">
              <ins>{shorten(row.newText, 220)}</ins>
            </span>
          ) : (
            <span className="app-text-diff">
              <del>{shorten(row.oldText, 220)}</del>
            </span>
          )}
        </li>
      ))}
      {rows.length > visible.length ? (
        <li className="app-changes-more">
          …и ещё {rows.length - visible.length}{" "}
          {pluralBlocks(rows.length - visible.length)}
        </li>
      ) : null}
    </ul>
  );
}

/** Краткое описание изменений для окна подтверждения. */
export function ChangesSummary({ edits }) {
  return (
    <ul className="app-changes-list">
      {edits.map((edit) => (
        <li key={edit.key} className="app-changes-entity">
          <strong>
            {KIND_LABELS[edit.kind] || "Элемент"} «{shorten(edit.label, 80)}»
          </strong>
          <ul className="app-changes-fields">
            {Object.keys(edit.changes)
              .filter((field) => !isDerivedDraftField(field))
              .map((field) => (
                <li key={field} className="app-changes-field">
                  <span className="app-changes-label">
                    {FIELD_LABELS[field] || field}
                  </span>
                  {field === "contentBlocks" ? (
                    <ContentBlocksChange
                      before={edit.original[field]}
                      after={edit.changes[field]}
                    />
                  ) : (
                    <TextDiff
                      before={textValue(edit.original[field])}
                      after={textValue(edit.changes[field])}
                    />
                  )}
                </li>
              ))}
          </ul>
          {edit.error ? (
            <p className="app-modal-error" role="alert">
              {edit.error}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

/**
 * Плашка «Есть несохранённые изменения» внизу редактора курса.
 * onSave(edits) сохраняет на backend и возвращает true, если всё сохранилось.
 * onDiscard(edits) возвращает интерфейс к исходным значениям.
 */
export default function EditorSaveBar({ courseId, onSave, onDiscard }) {
  const allEdits = useEditorDraftStore((state) => state.edits);
  const edits = useMemo(
    () => Object.values(allEdits).filter((edit) => edit.courseId === courseId),
    [allEdits, courseId],
  );
  const [dialog, setDialog] = useState(null);

  useEffect(() => {
    if (!edits.length) return undefined;
    const onBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [edits.length]);

  useEffect(() => {
    if (!edits.length) setDialog(null);
  }, [edits.length]);

  if (!edits.length && !dialog) return null;

  const count = edits.length;
  const label =
    count === 1
      ? "Есть несохранённые изменения"
      : `Несохранённые изменения: ${count}`;

  return (
    <>
      {count > 0 && (
        <div className="editor-save-bar" role="status">
          <strong>{label}</strong>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => setDialog("discard")}
          >
            Отменить изменения
          </button>
          <button
            type="button"
            className="btn btn-solid"
            onClick={() => setDialog("save")}
          >
            Сохранить
          </button>
        </div>
      )}

      <ConfirmDialog
        open={dialog === "save"}
        title="Сохранить изменения?"
        description="Проверьте, что будет изменено. Данные уйдут на сервер только после подтверждения."
        confirmLabel="Подтвердить"
        cancelLabel="Отмена"
        busyLabel="Сохраняем..."
        size="md"
        onCancel={() => setDialog(null)}
        onConfirm={async () => {
          const saved = await onSave(edits);
          if (saved) setDialog(null);
          return saved;
        }}
      >
        <ChangesSummary edits={edits} />
      </ConfirmDialog>

      <ConfirmDialog
        open={dialog === "discard"}
        title="Отменить несохранённые изменения?"
        description="Поля модулей и уроков вернутся к последней сохранённой версии. Это действие нельзя отменить."
        confirmLabel="Отменить изменения"
        cancelLabel="Продолжить редактирование"
        busyLabel="Отменяем..."
        danger
        size="md"
        onCancel={() => setDialog(null)}
        onConfirm={() => {
          onDiscard(edits);
          setDialog(null);
        }}
      >
        <ChangesSummary edits={edits} />
      </ConfirmDialog>
    </>
  );
}
