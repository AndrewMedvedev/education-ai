import { useEffect, useMemo, useState } from "react";
import SectionTop from "../components/SectionTop";
import { useSessionStore } from "../stores/sessionStore";
import {
  createOrganization,
  deleteOrganization,
  fetchOrganizationById,
  fetchOrganizationsPage,
  updateOrganization,
} from "../utils/api";

const EMPTY_FORM = {
  name: "",
  email: "",
  description: "",
};

function organizationToForm(organization) {
  return {
    name: organization?.name || "",
    email: organization?.email || "",
    description: organization?.description || "",
  };
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function FieldError({ message }) {
  return message ? (
    <span className="organization-field-error">{message}</span>
  ) : null;
}

function OrganizationMeta({ organization }) {
  return (
    <dl className="organization-meta">
      <div>
        <dt>Создана</dt>
        <dd>{formatDate(organization.created_at)}</dd>
      </div>
      <div>
        <dt>Обновлена</dt>
        <dd>{formatDate(organization.updated_at)}</dd>
      </div>
    </dl>
  );
}

function OrganizationHeader({
  organization,
  kicker,
  isEditing = false,
  editForm = EMPTY_FORM,
  validationErrors = {},
  onEditChange,
  onOpen,
  children,
}) {
  return (
    <div className="organization-card-summary">
      <div className="organization-card-title">
        {kicker && <span className="organization-kicker">{kicker}</span>}
        {isEditing ? (
          <>
            <label className="organization-inline-field">
              <span>Название</span>
              <input
                value={editForm.name}
                maxLength={255}
                onChange={(event) => onEditChange("name", event.target.value)}
              />
              <FieldError message={validationErrors.name} />
            </label>
            <label className="organization-inline-field">
              <span>Email</span>
              <input
                type="email"
                value={editForm.email}
                onChange={(event) => onEditChange("email", event.target.value)}
              />
              <FieldError message={validationErrors.email} />
            </label>
          </>
        ) : onOpen ? (
          <button
            type="button"
            className="organization-open-field"
            onClick={() => onOpen(organization)}
          >
            <strong>{organization.name}</strong>
            <span>{organization.email}</span>
          </button>
        ) : (
          <>
            <h4>{organization.name}</h4>
            <p>{organization.email}</p>
          </>
        )}
      </div>
      <div className="organization-card-actions">
        <span
          className={
            organization.is_active
              ? "organization-status"
              : "organization-status is-inactive"
          }
        >
          {organization.is_active ? "Активна" : "Неактивна"}
        </span>
        {children}
      </div>
    </div>
  );
}

function OrganizationForm({
  form,
  submitLabel,
  pendingLabel,
  isPending = false,
  validationErrors = {},
  onChange,
  onSubmit,
  onCancel,
  required = false,
}) {
  return (
    <form className="organization-form" onSubmit={onSubmit}>
      <label>
        <span>Название</span>
        <input
          value={form.name}
          maxLength={255}
          onChange={(event) => onChange("name", event.target.value)}
          required={required}
        />
        <FieldError message={validationErrors.name} />
      </label>
      <label>
        <span>Email</span>
        <input
          type="email"
          value={form.email}
          onChange={(event) => onChange("email", event.target.value)}
          required={required}
        />
        <FieldError message={validationErrors.email} />
      </label>
      <label className="organization-form-wide">
        <span>Описание</span>
        <textarea
          value={form.description}
          onChange={(event) => onChange("description", event.target.value)}
          required={required}
        />
        <FieldError message={validationErrors.description} />
      </label>
      <div className="organization-form-actions organization-form-wide">
        <button type="submit" className="btn btn-solid" disabled={isPending}>
          {isPending ? pendingLabel : submitLabel}
        </button>
        {onCancel && (
          <button
            type="button"
            className="btn btn-outline"
            disabled={isPending}
            onClick={onCancel}
          >
            Отмена
          </button>
        )}
      </div>
    </form>
  );
}

function OrganizationDetails({
  organization,
  title = "Организация",
  canUpdateOrganization,
  canDeleteOrganization,
  editForm,
  validationErrors,
  pendingAction,
  isEditing,
  onStartEdit,
  onCancelEdit,
  onEditChange,
  onUpdate,
  onDelete,
}) {
  if (!organization) return null;

  return (
    <article className="glass-card organization-panel">
      <div className="organization-panel-head">
        <div>
          <span className="organization-kicker">{title}</span>
          <h3>{organization.name}</h3>
        </div>
        {canUpdateOrganization && !isEditing && (
          <button
            type="button"
            className="btn btn-outline"
            onClick={onStartEdit}
          >
            Редактировать
          </button>
        )}
      </div>

      <article className="organization-card">
        <OrganizationHeader
          organization={organization}
          isEditing={isEditing && canUpdateOrganization}
          editForm={editForm}
          validationErrors={validationErrors}
          onEditChange={onEditChange}
        />
        {isEditing && canUpdateOrganization ? (
          <label className="organization-inline-field organization-inline-description">
            <span>Описание</span>
            <textarea
              value={editForm.description}
              onChange={(event) =>
                onEditChange("description", event.target.value)
              }
            />
            <FieldError message={validationErrors.description} />
          </label>
        ) : (
          <p className="organization-description">
            {organization.description || "Описание не заполнено."}
          </p>
        )}
        <OrganizationMeta organization={organization} />

        {isEditing && canUpdateOrganization && (
          <div className="organization-form-actions">
            <button
              type="button"
              className="btn btn-solid"
              disabled={pendingAction === `update:${organization.id}`}
              onClick={() => onUpdate(organization.id, editForm)}
            >
              {pendingAction === `update:${organization.id}`
                ? "Сохраняем..."
                : "Сохранить"}
            </button>
            <button
              type="button"
              className="btn btn-outline"
              disabled={pendingAction === `update:${organization.id}`}
              onClick={onCancelEdit}
            >
              Отмена
            </button>
          </div>
        )}

        {canDeleteOrganization && organization.is_active && (
          <button
            type="button"
            className="btn btn-outline organization-danger-btn"
            disabled={pendingAction === `delete:${organization.id}`}
            onClick={() => onDelete(organization.id)}
          >
            {pendingAction === `delete:${organization.id}`
              ? "Удаляем..."
              : "Деактивировать"}
          </button>
        )}
      </article>
    </article>
  );
}

export default function OrganizationsPage({
  canCreateOrganization = false,
  canReadOrganization = false,
  canReadOwnOrganization = false,
  canUpdateOrganization = false,
  canDeleteOrganization = false,
}) {
  const organizationId = useSessionStore((state) => state.organizationId);
  const [activeSection, setActiveSection] = useState("current");
  const [currentOrganization, setCurrentOrganization] = useState(null);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [currentLoading, setCurrentLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [editForms, setEditForms] = useState({});
  const [editingOrganizationId, setEditingOrganizationId] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [pendingAction, setPendingAction] = useState("");

  const selectedOrganization = useMemo(() => {
    if (!selectedOrganizationId) return null;
    if (currentOrganization?.id === selectedOrganizationId)
      return currentOrganization;
    return (
      organizations.find((item) => item.id === selectedOrganizationId) || null
    );
  }, [currentOrganization, organizations, selectedOrganizationId]);

  const pages = useMemo(
    () =>
      Array.from({ length: Math.max(1, totalPages) }, (_, index) => index + 1),
    [totalPages],
  );

  const applyEditForm = (organization) => {
    if (!organization?.id) return;
    setEditForms((current) => ({
      ...current,
      [organization.id]: organizationToForm(organization),
    }));
  };

  const loadCurrentOrganization = async () => {
    if (!organizationId) {
      setCurrentOrganization(null);
      return;
    }

    const organizationFromList = organizations.find(
      (organization) => organization.id === organizationId,
    );

    if (organizationFromList) {
      setCurrentOrganization(organizationFromList);
      applyEditForm(organizationFromList);
      if (!selectedOrganizationId) {
        setSelectedOrganizationId(organizationFromList.id);
      }
      return;
    }
    if (!canReadOwnOrganization) {
      return;
    }

    setCurrentLoading(true);
    setError("");

    try {
      const organization = await fetchOrganizationById(organizationId);
      setCurrentOrganization(organization);
      applyEditForm(organization);
      if (!selectedOrganizationId) {
        setSelectedOrganizationId(organization.id);
      }
    } catch (loadError) {
      setCurrentOrganization(null);
      setError(
        loadError.userMessage ||
          loadError.message ||
          "Не удалось загрузить текущую организацию.",
      );
    } finally {
      setCurrentLoading(false);
    }
  };

  const loadOrganizations = async ({ silent = false } = {}) => {
    if (!canReadOrganization) {
      setOrganizations([]);
      setTotalPages(1);
      setTotalItems(0);
      return;
    }

    if (!silent) {
      setListLoading(true);
    }
    setError("");

    try {
      const response = await fetchOrganizationsPage({ page, size: pageSize });
      const items = response.items || [];
      setOrganizations(items);
      setTotalPages(response.total_pages || 1);
      setTotalItems(response.total_items || response.total || 0);

      const currentFromList = items.find(
        (organization) => organization.id === organizationId,
      );
      if (currentFromList) {
        setCurrentOrganization(currentFromList);
        if (!selectedOrganizationId) {
          setSelectedOrganizationId(currentFromList.id);
        }
      }
      setEditForms((current) => ({
        ...current,
        ...Object.fromEntries(
          items.map((organization) => [
            organization.id,
            organizationToForm(organization),
          ]),
        ),
      }));
    } catch (loadError) {
      setError(
        loadError.userMessage ||
          loadError.message ||
          "Не удалось загрузить организации.",
      );
      setOrganizations([]);
      setTotalPages(1);
      setTotalItems(0);
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadCurrentOrganization();
  }, [
    organizationId,
    canReadOrganization,
    canReadOwnOrganization,
    organizations,
  ]);

  useEffect(() => {
    loadOrganizations();
  }, [canReadOrganization, page, pageSize]);

  useEffect(() => {
    if (!notice && !error) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setNotice("");
      setError("");
    }, 4000);

    return () => window.clearTimeout(timeoutId);
  }, [notice, error]);

  const updateCreateField = (field, value) => {
    setCreateForm((current) => ({ ...current, [field]: value }));
    setValidationErrors((current) => ({ ...current, [field]: "" }));
  };

  const updateEditField = (organizationIdToEdit, field, value) => {
    setEditForms((current) => ({
      ...current,
      [organizationIdToEdit]: {
        ...(current[organizationIdToEdit] || EMPTY_FORM),
        [field]: value,
      },
    }));
    setValidationErrors((current) => ({ ...current, [field]: "" }));
  };

  const openCurrentOrganization = () => {
    setActiveSection("current");
    setSelectedOrganizationId(
      currentOrganization?.id || organizationId || null,
    );
    setEditingOrganizationId(null);
    setValidationErrors({});
  };

  const openCreateOrganization = () => {
    setActiveSection("create");
    setEditingOrganizationId(null);
    setValidationErrors({});
  };

  const openAllOrganizations = () => {
    if (!canReadOrganization) return;
    setActiveSection("all");
    setSelectedOrganizationId(null);
    setEditingOrganizationId(null);
    setValidationErrors({});
  };

  const openOrganizationDetails = (organization) => {
    setActiveSection("details");
    setSelectedOrganizationId(organization.id);
    setEditingOrganizationId(null);
    setValidationErrors({});
    applyEditForm(organization);
  };

  const startEditingOrganization = (organization) => {
    applyEditForm(organization);
    setEditingOrganizationId(organization.id);
    setValidationErrors({});
  };

  const cancelEditingOrganization = () => {
    if (selectedOrganization) applyEditForm(selectedOrganization);
    if (currentOrganization) applyEditForm(currentOrganization);
    setEditingOrganizationId(null);
    setValidationErrors({});
  };

  const refreshAfterMutation = async (organizationIdToRefresh) => {
    if (organizationIdToRefresh === organizationId) {
      await loadCurrentOrganization();
    }
    if (canReadOrganization) {
      await loadOrganizations({ silent: true });
    }
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!canCreateOrganization) return;

    setPendingAction("create");
    setError("");
    setNotice("");
    setValidationErrors({});

    try {
      const organization = await createOrganization(createForm);
      setCreateForm(EMPTY_FORM);
      setNotice("Организация создана.");
      if (canReadOrganization && organization?.id) {
        applyEditForm(organization);
        setOrganizations((current) => [
          organization,
          ...current.filter((item) => item.id !== organization.id),
        ]);
        setSelectedOrganizationId(organization.id);
        setActiveSection("details");
        setPage(1);
        await loadOrganizations({ silent: true });
      } else {
        openCurrentOrganization();
      }
    } catch (createError) {
      setValidationErrors(createError.validationErrors || {});
      setError(
        createError.userMessage ||
          createError.message ||
          "Не удалось создать организацию.",
      );
    } finally {
      setPendingAction("");
    }
  };

  const handleUpdate = async (organizationIdToUpdate, form) => {
    if (!canUpdateOrganization || !organizationIdToUpdate) return;

    setPendingAction(`update:${organizationIdToUpdate}`);
    setError("");
    setNotice("");
    setValidationErrors({});

    try {
      const organization = await updateOrganization(
        organizationIdToUpdate,
        form,
      );
      setNotice("Организация обновлена.");
      setEditingOrganizationId(null);
      if (organization?.id) {
        applyEditForm(organization);
        if (organization.id === organizationId)
          setCurrentOrganization(organization);
        setOrganizations((current) =>
          current.map((item) =>
            item.id === organization.id ? organization : item,
          ),
        );
      }
      await refreshAfterMutation(organizationIdToUpdate);
    } catch (updateError) {
      setValidationErrors(updateError.validationErrors || {});
      setError(
        updateError.userMessage ||
          updateError.message ||
          "Не удалось обновить организацию.",
      );
    } finally {
      setPendingAction("");
    }
  };

  const handleDelete = async (organizationIdToDelete) => {
    if (!canDeleteOrganization || !organizationIdToDelete) return;

    setPendingAction(`delete:${organizationIdToDelete}`);
    setError("");
    setNotice("");

    try {
      await deleteOrganization(organizationIdToDelete);
      setNotice("Организация деактивирована.");
      await refreshAfterMutation(organizationIdToDelete);
    } catch (deleteError) {
      setError(
        deleteError.userMessage ||
          deleteError.message ||
          "Не удалось удалить организацию.",
      );
    } finally {
      setPendingAction("");
    }
  };

  const renderDetails = (organization, title) => (
    <OrganizationDetails
      organization={organization}
      title={title}
      canUpdateOrganization={canUpdateOrganization}
      canDeleteOrganization={canDeleteOrganization}
      editForm={editForms[organization?.id] || EMPTY_FORM}
      validationErrors={validationErrors}
      pendingAction={pendingAction}
      isEditing={editingOrganizationId === organization?.id}
      onStartEdit={() => startEditingOrganization(organization)}
      onCancelEdit={cancelEditingOrganization}
      onEditChange={(field, value) =>
        updateEditField(organization.id, field, value)
      }
      onUpdate={handleUpdate}
      onDelete={handleDelete}
    />
  );

  return (
    <section className="container section organizations-page">
      <SectionTop
        label="Организации"
        title="Управление организациями платформы"
      />
      <p className="courses-catalog-intro">
        По умолчанию отображается организация, в которой состоит текущий
        пользователь. Остальные разделы в дереве появляются только при наличии
        соответствующих permissions.
      </p>

      {(notice || error) && (
        <article
          className={`glass-card organization-message ${error ? "is-error" : ""}`}
        >
          <p>{error || notice}</p>
        </article>
      )}

      <div className="organizations-layout">
        <aside
          className="glass-card organizations-tree"
          aria-label="Дерево организаций"
        >
          <button
            type="button"
            className={`organizations-tree-item ${activeSection === "current" ? "is-active" : ""}`}
            onClick={openCurrentOrganization}
          >
            <span>Текущая организация</span>
            {currentOrganization?.name && (
              <small>{currentOrganization.name}</small>
            )}
          </button>

          {canCreateOrganization && (
            <button
              type="button"
              className={`organizations-tree-item ${activeSection === "create" ? "is-active" : ""}`}
              onClick={openCreateOrganization}
            >
              <span>Создание организации</span>
            </button>
          )}

          {canReadOrganization && (
            <div className="organizations-tree-group">
              <button
                type="button"
                className={`organizations-tree-item ${activeSection === "all" ? "is-active" : ""}`}
                onClick={openAllOrganizations}
              >
                <span>Все организации</span>
              </button>
              {(activeSection === "all" || activeSection === "details") &&
                organizations.length > 0 && (
                  <>
                    <div className="organizations-tree-children">
                      {organizations.map((organization) => (
                        <button
                          key={organization.id}
                          type="button"
                          className={`organizations-tree-child ${selectedOrganizationId === organization.id ? "is-active" : ""}`}
                          onClick={() => openOrganizationDetails(organization)}
                        >
                          {organization.name}
                        </button>
                      ))}
                    </div>
                    {totalPages > 1 && (
                      <div className="organizations-tree-pagination">
                        <button
                          type="button"
                          disabled={page <= 1}
                          onClick={() =>
                            setPage((current) => Math.max(1, current - 1))
                          }
                        >
                          Назад
                        </button>
                        <span>
                          {page}/{totalPages}
                        </span>
                        <button
                          type="button"
                          disabled={page >= totalPages}
                          onClick={() =>
                            setPage((current) =>
                              Math.min(totalPages, current + 1),
                            )
                          }
                        >
                          Вперёд
                        </button>
                      </div>
                    )}
                  </>
                )}
            </div>
          )}
        </aside>

        <div className="organizations-content">
          {activeSection === "current" && (
            <>
              {currentLoading && (
                <article className="glass-card organization-panel">
                  <p className="organization-muted">
                    Загружаем текущую организацию...
                  </p>
                </article>
              )}
              {!currentLoading &&
                currentOrganization &&
                renderDetails(currentOrganization, "Текущая организация")}
              {!currentLoading && !currentOrganization && !error && (
                <article className="glass-card organization-panel">
                  <h3>Текущая организация не определена</h3>
                  <p className="organization-muted">
                    В сессии нет organization_id или данные организации
                    недоступны.
                  </p>
                </article>
              )}
            </>
          )}

          {activeSection === "create" && canCreateOrganization && (
            <article className="glass-card organization-panel">
              <div className="organization-panel-head">
                <div>
                  <h3>Создание организации</h3>
                </div>
              </div>
              <OrganizationForm
                form={createForm}
                submitLabel="Создать"
                pendingLabel="Создаём..."
                isPending={pendingAction === "create"}
                validationErrors={validationErrors}
                onChange={updateCreateField}
                onSubmit={handleCreate}
                required
              />
            </article>
          )}

          {activeSection === "details" &&
            selectedOrganization &&
            renderDetails(selectedOrganization, "Организация")}

          {activeSection === "all" && canReadOrganization && (
            <article className="glass-card organization-panel">
              <div className="organization-panel-head">
                <div>
                  <span className="organization-kicker">organization.read</span>
                  <h3>Все организации</h3>
                </div>
              </div>

              {listLoading && (
                <p className="organization-muted">Загружаем организации...</p>
              )}
              {!listLoading && organizations.length === 0 && !error && (
                <p className="organization-muted">
                  Организации пока не найдены.
                </p>
              )}

              {!listLoading && organizations.length > 0 && (
                <div className="organization-list">
                  {organizations.map((organization) => (
                    <article
                      key={organization.id}
                      className="organization-card"
                    >
                      <OrganizationHeader
                        organization={organization}
                        onOpen={openOrganizationDetails}
                      >
                        {canUpdateOrganization && (
                          <button
                            type="button"
                            className="btn btn-outline"
                            onClick={() => {
                              openOrganizationDetails(organization);
                              startEditingOrganization(organization);
                            }}
                          >
                            Редактировать
                          </button>
                        )}
                      </OrganizationHeader>
                      <p className="organization-description">
                        {organization.description || "Описание не заполнено."}
                      </p>
                      <OrganizationMeta organization={organization} />
                      {canDeleteOrganization && organization.is_active && (
                        <div className="organization-card-actions-row">
                          <button
                            type="button"
                            className="btn btn-outline organization-danger-btn"
                            disabled={
                              pendingAction === `delete:${organization.id}`
                            }
                            onClick={() => handleDelete(organization.id)}
                          >
                            {pendingAction === `delete:${organization.id}`
                              ? "Удаляем..."
                              : "Деактивировать"}
                          </button>
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              )}

              {totalPages > 1 && (
                <nav
                  className="courses-pagination"
                  aria-label="Пагинация организаций"
                >
                  <span>
                    Страница {page} из {totalPages}
                  </span>
                  <div className="courses-pagination-actions">
                    <button
                      type="button"
                      className="btn btn-outline"
                      disabled={page <= 1}
                      onClick={() =>
                        setPage((current) => Math.max(1, current - 1))
                      }
                    >
                      Назад
                    </button>
                    {pages.map((pageNumber) => (
                      <button
                        key={pageNumber}
                        type="button"
                        className={`courses-pagination-page ${pageNumber === page ? "is-active" : ""}`}
                        onClick={() => setPage(pageNumber)}
                        aria-current={pageNumber === page ? "page" : undefined}
                      >
                        {pageNumber}
                      </button>
                    ))}
                    <button
                      type="button"
                      className="btn btn-outline"
                      disabled={page >= totalPages}
                      onClick={() =>
                        setPage((current) => Math.min(totalPages, current + 1))
                      }
                    >
                      Вперёд
                    </button>
                  </div>
                </nav>
              )}
            </article>
          )}
        </div>
      </div>
    </section>
  );
}
