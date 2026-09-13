import { useEffect, useMemo, useState } from "react";
import SectionTop from "../components/SectionTop";
import { useModelStore } from "../stores/modelStore";

function FieldError({ message }) {
  return message ? <span className="model-field-error">{message}</span> : null;
}

function ModelForm({
  form,
  validationErrors,
  isCreating,
  onChange,
  onSubmit,
  onCancel,
}) {
  return (
    <form className="model-form" onSubmit={onSubmit}>
      <label>
        <span>Название</span>
        <input
          value={form.name}
          maxLength={255}
          onChange={(event) => onChange("name", event.target.value)}
          required
        />
        <FieldError message={validationErrors.name} />
      </label>
      <label className="model-form-wide">
        <span>Описание</span>
        <textarea
          value={form.description}
          onChange={(event) => onChange("description", event.target.value)}
        />
        <FieldError message={validationErrors.description} />
      </label>
      <label className="model-form-wide">
        <span>Контекст</span>
        <textarea
          className="model-context-input"
          value={form.context}
          onChange={(event) => onChange("context", event.target.value)}
        />
        <FieldError message={validationErrors.context} />
      </label>
      <FieldError message={validationErrors.form} />
      <div className="model-form-actions model-form-wide">
        <button type="submit" className="btn btn-solid" disabled={isCreating}>
          {isCreating ? "Создаём..." : "Создать модель"}
        </button>
        <button
          type="button"
          className="btn btn-outline"
          disabled={isCreating}
          onClick={onCancel}
        >
          Очистить
        </button>
      </div>
    </form>
  );
}

function splitModelDescription(description = "") {
  const text = description.trim();
  if (!text) return [];

  const matches = Array.from(text.matchAll(/([A-Z_]{2,}):\s*/g));
  if (matches.length === 0) {
    return [{ label: "Описание", value: text }];
  }

  return matches
    .map((match, index) => {
      const nextMatch = matches[index + 1];
      const valueStart = match.index + match[0].length;
      const valueEnd = nextMatch?.index ?? text.length;
      return {
        label: match[1].replaceAll("_", " "),
        value: text.slice(valueStart, valueEnd).replace(/^[-—.\s]+|\s+$/g, ""),
      };
    })
    .filter((item) => item.value);
}

function ModelDescription({ description }) {
  const parts = splitModelDescription(description);

  if (parts.length === 0) {
    return <p className="model-description-empty">Описание не заполнено.</p>;
  }

  return (
    <div className="model-description-grid">
      {parts.map((part) => (
        <section key={part.label} className="model-description-item">
          <span>{part.label}</span>
          <p>{part.value}</p>
        </section>
      ))}
    </div>
  );
}

function ModelCard({ model, canDeleteModel, deletingUid, onDelete }) {
  const isDeleting = deletingUid === model.uid;

  return (
    <article className="model-card">
      <div className="model-card-summary">
        <div className="model-card-title">
          <span className="model-kicker">AIModel</span>
          <h4>{model.name}</h4>
        </div>
        {canDeleteModel && (
          <button
            type="button"
            className="btn btn-outline model-danger-btn"
            disabled={isDeleting}
            onClick={() => onDelete(model)}
          >
            {isDeleting ? "Удаляем..." : "Удалить"}
          </button>
        )}
      </div>
      <ModelDescription description={model.description} />
      {model.context && (
        <div className="model-card-footer">
          <div className="model-context-chip" title="Контекстное окно модели">
            <span>Контекст</span>
            <strong>{model.context}</strong>
          </div>
        </div>
      )}
    </article>
  );
}

export default function ModelsPage({
  canCreateModel = false,
  canDeleteModel = false,
}) {
  const items = useModelStore((state) => state.items);
  const page = useModelStore((state) => state.page);
  const size = useModelStore((state) => state.size);
  const total = useModelStore((state) => state.total);
  const totalPages = useModelStore((state) => state.totalPages);
  const isLoading = useModelStore((state) => state.isLoading);
  const isCreating = useModelStore((state) => state.isCreating);
  const deletingUid = useModelStore((state) => state.deletingUid);
  const error = useModelStore((state) => state.error);
  const notice = useModelStore((state) => state.notice);
  const validationErrors = useModelStore((state) => state.validationErrors);
  const createForm = useModelStore((state) => state.createForm);
  const setPage = useModelStore((state) => state.setPage);
  const updateCreateField = useModelStore((state) => state.updateCreateField);
  const resetCreateForm = useModelStore((state) => state.resetCreateForm);
  const clearMessages = useModelStore((state) => state.clearMessages);
  const setNotice = useModelStore((state) => state.setNotice);
  const fetchModels = useModelStore((state) => state.fetchModels);
  const createModel = useModelStore((state) => state.createModel);
  const deleteModel = useModelStore((state) => state.deleteModel);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const pages = useMemo(
    () =>
      Array.from({ length: Math.max(1, totalPages) }, (_, index) => index + 1),
    [totalPages],
  );

  useEffect(() => {
    fetchModels(page, size).catch(() => {});
  }, [fetchModels, page, size]);

  useEffect(() => {
    if (!notice && !error) return undefined;

    const timeoutId = window.setTimeout(() => {
      clearMessages();
    }, 4000);

    return () => window.clearTimeout(timeoutId);
  }, [notice, error, clearMessages]);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!canCreateModel || isCreating) return;

    try {
      await createModel(createForm);
      setShowCreateForm(false);
    } catch {
      // Ошибка уже переложена в store для отображения в UI.
    }
  };

  const handleDelete = async (model) => {
    if (!canDeleteModel || !model?.uid || deletingUid) return;

    const confirmed = window.confirm(
      `Удалить AI-модель «${model.name || model.uid}»? Это действие нельзя отменить.`,
    );
    if (!confirmed) return;

    try {
      await deleteModel(model.uid);
    } catch {
      // Ошибка уже переложена в store для отображения в UI.
    }
  };

  const openCreateForm = () => {
    if (!canCreateModel) return;
    clearMessages();
    setShowCreateForm(true);
  };

  const cancelCreate = () => {
    resetCreateForm();
    setShowCreateForm(false);
    setNotice("");
  };

  return (
    <section className="container section models-page">
      <SectionTop label="AI-модели" title="Управление AI-моделями" />
      <p className="courses-catalog-intro">
        Просмотр списка доступен авторизованным пользователям. Создание и
        удаление отображаются только при наличии соответствующих permissions.
      </p>

      {(notice || error) && (
        <article
          className={`glass-card model-message ${error ? "is-error" : ""}`}
        >
          <p>{error || notice}</p>
        </article>
      )}

      <article className="glass-card model-panel">
        <div className="model-panel-head">
          <div>
            <span className="model-kicker">/ai/models</span>
            <h3>Список моделей</h3>
            <p className="model-muted">Всего: {total}</p>
          </div>
          {canCreateModel && !showCreateForm && (
            <button
              type="button"
              className="btn btn-solid"
              onClick={openCreateForm}
            >
              Создать модель
            </button>
          )}
        </div>

        {showCreateForm && canCreateModel && (
          <div className="model-create-box">
            <div className="model-panel-head">
              <h4>Новая AI-модель</h4>
              <button
                type="button"
                className="btn btn-outline"
                disabled={isCreating}
                onClick={cancelCreate}
              >
                Закрыть
              </button>
            </div>
            <ModelForm
              form={createForm}
              validationErrors={validationErrors}
              isCreating={isCreating}
              onChange={updateCreateField}
              onSubmit={handleCreate}
              onCancel={resetCreateForm}
            />
          </div>
        )}

        {isLoading && <p className="model-muted">Загружаем AI-модели...</p>}
        {!isLoading && items.length === 0 && !error && (
          <p className="model-muted">AI-модели пока не найдены.</p>
        )}

        {!isLoading && items.length > 0 && (
          <div className="model-list">
            {items.map((model) => (
              <ModelCard
                key={model.uid}
                model={model}
                canDeleteModel={canDeleteModel}
                deletingUid={deletingUid}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <nav className="courses-pagination" aria-label="Пагинация AI-моделей">
            <span>
              Страница {page} из {totalPages}
            </span>
            <div className="courses-pagination-actions">
              <button
                type="button"
                className="btn btn-outline"
                disabled={page <= 1 || isLoading}
                onClick={() => setPage(Math.max(1, page - 1))}
              >
                Назад
              </button>
              {pages.map((pageNumber) => (
                <button
                  key={pageNumber}
                  type="button"
                  className={`courses-pagination-page ${pageNumber === page ? "is-active" : ""}`}
                  disabled={isLoading}
                  onClick={() => setPage(pageNumber)}
                  aria-current={pageNumber === page ? "page" : undefined}
                >
                  {pageNumber}
                </button>
              ))}
              <button
                type="button"
                className="btn btn-outline"
                disabled={page >= totalPages || isLoading}
                onClick={() => setPage(Math.min(totalPages, page + 1))}
              >
                Вперёд
              </button>
            </div>
          </nav>
        )}
      </article>
    </section>
  );
}
