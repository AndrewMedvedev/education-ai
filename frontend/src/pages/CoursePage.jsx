// Страница деталей выбранного курса с описанием, блоками и лидербордом
import { Fragment, useState } from "react";
import SectionTop from "../components/SectionTop";
import CourseNavigationTree from "../components/CourseNavigationTree";
import CourseInviteDialog from "../components/course/CourseInviteDialog";
import AgentInterviewDialog, {
  resetAgentInterview,
} from "../components/editor/AgentInterviewDialog";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import { useGoBack } from "../hooks/useGoBack";
import {
  generationJobKey,
  useGenerationJobsStore,
} from "../stores/generationJobsStore";
import { useSessionStore } from "../stores/sessionStore";
import { isUuid } from "../utils/api";

// На странице курса в дереве не выделен ни один модуль.
const NO_SELECTED_BLOCK = { id: "" };

export default function CoursePage({
  selectedCourse,
  selectedCourseLeaderboard,
  completedLessons,
  completedPractices,
  openBlock,
  openLesson,
  openPractice,
  isCourseEditMode,
  setIsCourseEditMode,
  canReadCourse,
  canUpdateCourse,
  canDeleteCourse,
  deleteCourse,
  updateCourseStatus,
  updateCourse,
  updateCourseBlock,
  insertCourseBlock,
  moveBlock,
  deleteBlock,
}) {
  const [activeBlockId, setActiveBlockId] = useState(null);
  const [statusAction, setStatusAction] = useState("");
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  // Позиция в списке модулей, где открыт чат генерации модуля (null — закрыт).
  const [moduleAgentIndex, setModuleAgentIndex] = useState(null);
  const [isModuleChatVisible, setIsModuleChatVisible] = useState(true);
  // { type: "module" | "course", id, title } — что пользователь хочет удалить.
  const [pendingDelete, setPendingDelete] = useState(null);
  const currentUserId = useSessionStore(
    (state) => state.identity?.id || state.user?.id || "",
  );
  const moduleJob = useGenerationJobsStore(
    (state) =>
      state.jobs[generationJobKey("module", selectedCourse.id, "")] || null,
  );
  const goBack = useGoBack({ fallbackPath: "/courses" });

  if (!canReadCourse) {
    return (
      <section className="container section course-details-view">
        <SectionTop label="Курс" title="Доступ ограничен" />
        <article className="glass-card course-details-main">
          <p className="course-details-text">
            Курс недоступен для вашего аккаунта. Обратитесь к администратору
            организации, чтобы получить доступ.
          </p>
          <button type="button" className="btn btn-outline" onClick={goBack}>
            Вернуться к каталогу
          </button>
        </article>
      </section>
    );
  }

  const totalLessonsInCourse = selectedCourse.blocks.reduce(
    (total, block) => total + block.lessons.length,
    0,
  );

  const learningObjectives = selectedCourse.learningObjectives || [];

  const updateObjective = (index, value) => {
    const next = [...learningObjectives];
    next[index] = value;
    updateCourse({ learningObjectives: next });
  };

  const addObjective = () => {
    updateCourse({ learningObjectives: [...learningObjectives, ""] });
  };

  const removeObjective = (index) => {
    updateCourse({
      learningObjectives: learningObjectives.filter(
        (_, itemIndex) => itemIndex !== index,
      ),
    });
  };

  const insertBlock = async (index) => {
    const blockId = await insertCourseBlock(index);
    if (blockId) {
      setActiveBlockId(blockId);
    }
  };

  const changeStatus = async (action) => {
    if (!updateCourseStatus || statusAction) return;
    setStatusAction(action);
    try {
      await updateCourseStatus(selectedCourse.id, action);
    } finally {
      setStatusAction("");
    }
  };

  const canGenerateModule = isCourseEditMode && isUuid(selectedCourse.id);
  // Пока идёт генерация, чат держим в месте, куда вставится модуль.
  const moduleAgentAt =
    moduleJob && Number.isFinite(Number(moduleJob.order))
      ? Number(moduleJob.order) - 1
      : moduleAgentIndex;

  const describeModulePosition = (index) => {
    const blocks = selectedCourse.blocks;
    if (!blocks.length) return "Модуль станет первым в курсе.";
    if (index <= 0)
      return `Модуль встанет в начало, перед «${blocks[0].title}».`;
    if (index >= blocks.length) {
      return `Модуль встанет в конец, после «${blocks[blocks.length - 1].title}».`;
    }
    return `Модуль встанет между «${blocks[index - 1].title}» и «${blocks[index].title}».`;
  };

  const isModuleJobRunning = moduleJob?.status === "running";

  // Открывает чат у выбранного места или переносит туда уже открытый чат — окно не
  // закрывается. Пока генерация идёт, место менять нельзя: модуль уже ставится в очередь
  // именно сюда. После готового или упавшего запуска начинаем новый диалог.
  const openModuleAgent = (index) => {
    const currentJob =
      useGenerationJobsStore.getState().jobs[
        generationJobKey("module", selectedCourse.id, "")
      ];
    if (currentJob?.status === "running") return;
    if (currentJob) {
      resetAgentInterview({ kind: "module", courseId: selectedCourse.id });
    }
    setModuleAgentIndex(index);
    setIsModuleChatVisible(true);
  };

  // Пока генерация идёт, окно только прячется: метка в списке остаётся.
  // Готовую или упавшую генерацию закрытие завершает — метка пропадает.
  const closeModuleAgent = () => {
    const currentJob =
      useGenerationJobsStore.getState().jobs[
        generationJobKey("module", selectedCourse.id, "")
      ];
    if (currentJob?.status === "running") {
      setIsModuleChatVisible(false);
      return;
    }
    if (currentJob) {
      resetAgentInterview({ kind: "module", courseId: selectedCourse.id });
    }
    setModuleAgentIndex(null);
  };

  const renderInsertControl = (index) => {
    if (!isCourseEditMode) return null;
    if (canGenerateModule && moduleAgentAt === index) {
      // Кнопки стоят на месте, а сюда встанет модуль из плавающего окна чата.
      return (
        <li className="course-agent-marker" key={`insert-${index}`}>
          <span>
            {moduleJob?.status === "running"
              ? moduleJob.resultId
                ? `✦ Модуль «${moduleJob.resultTitle || "без названия"}» генерируется — ниже`
                : "✦ Здесь появится модуль — генерация идёт"
              : moduleJob?.status === "done"
                ? "✦ Модуль сгенерирован — ниже"
                : "✦ Сюда встанет модуль из чата с ИИ"}
          </span>
          <div>
            {!isModuleChatVisible && (
              <button
                type="button"
                onClick={() => setIsModuleChatVisible(true)}
              >
                Показать чат
              </button>
            )}
            {!moduleJob && (
              <button type="button" onClick={() => setModuleAgentIndex(null)}>
                Отменить
              </button>
            )}
          </div>
        </li>
      );
    }
    return (
      <li className="course-block-insert" key={`insert-${index}`}>
        <div className="course-insert-actions">
          <button type="button" onClick={() => insertBlock(index)}>
            Вставить пустой модуль
          </button>
          {canGenerateModule && (
            <button
              type="button"
              className="is-ai"
              onClick={() => openModuleAgent(index)}
              disabled={isModuleJobRunning}
              title={
                isModuleJobRunning
                  ? "Дождитесь окончания текущей генерации модуля"
                  : undefined
              }
            >
              {moduleAgentAt === null
                ? "✦ Сгенерировать модуль с ИИ"
                : "✦ Сгенерировать модуль здесь"}
            </button>
          )}
        </div>
      </li>
    );
  };

  return (
    <section className="container section course-details-view is-course-edit-layout">
      <SectionTop label="Курс" title={selectedCourse.title} />
      {canUpdateCourse ? (
        <CourseInviteDialog
          open={isInviteOpen}
          onClose={() => setIsInviteOpen(false)}
          courseId={selectedCourse.id}
          courseTitle={selectedCourse.title}
          canViewMembers
          currentUserId={currentUserId}
        />
      ) : null}
      <button
        type="button"
        className="btn btn-outline back-btn"
        onClick={goBack}
        aria-label="Назад к каталогу"
        title="Назад к каталогу"
      >
        &lt;
      </button>
      {/* Та же сетка, что в режиме обучения: дерево курса слева, содержимое справа. */}
      <div className="course-edit-grid">
        <CourseNavigationTree
          selectedCourse={selectedCourse}
          selectedBlock={NO_SELECTED_BLOCK}
          selectedLessonId=""
          selectedPracticeId=""
          completedLessons={completedLessons}
          completedPractices={completedPractices}
          openBlock={openBlock}
          openLesson={openLesson}
          openPractice={openPractice}
          mode="theory"
        />
        <div className="course-edit-main">
          <div className="course-page-actions">
            {canUpdateCourse && selectedCourse.status !== "archived" && (
              <button
                type="button"
                className="btn btn-outline course-invite-toggle"
                onClick={() => setIsInviteOpen(true)}
              >
                Пригласить
              </button>
            )}
            {canUpdateCourse && !isCourseEditMode && (
              <button
                type="button"
                className="btn btn-outline course-edit-toggle"
                onClick={() => setIsCourseEditMode(true)}
              >
                Редактировать курс
              </button>
            )}
            {isCourseEditMode &&
              canUpdateCourse &&
              selectedCourse.status !== "archived" && (
                <>
                  {selectedCourse.status !== "published" && (
                    <button
                      type="button"
                      className="btn btn-outline"
                      onClick={() => changeStatus("publish")}
                      disabled={statusAction === "publish"}
                    >
                      {statusAction === "publish"
                        ? "Публикуем..."
                        : "Опубликовать"}
                    </button>
                  )}
                  {selectedCourse.status !== "invite_only" && (
                    <button
                      type="button"
                      className="btn btn-outline"
                      onClick={() => changeStatus("invite_only")}
                      disabled={statusAction === "invite_only"}
                    >
                      {statusAction === "invite_only"
                        ? "Сохраняем..."
                        : "Только для приглашённых"}
                    </button>
                  )}
                </>
              )}
            {isCourseEditMode &&
              canDeleteCourse &&
              selectedCourse.status !== "archived" && (
                <button
                  type="button"
                  className="btn btn-outline course-delete-btn"
                  onClick={() =>
                    setPendingDelete({
                      type: "course",
                      id: selectedCourse.id,
                      title: selectedCourse.title,
                    })
                  }
                  disabled={statusAction === "archive"}
                >
                  {statusAction === "archive" ? "Удаляем..." : "Удалить курс"}
                </button>
              )}
          </div>
          <div className="course-details-grid">
            <article className="glass-card course-details-main">
              {isCourseEditMode && (
                <div className="course-editor-panel course-meta-editor-panel">
                  <div className="course-editor-grid">
                    <label className="course-editor-field">
                      <span>Название курса</span>
                      <input
                        value={selectedCourse.title}
                        onChange={(event) =>
                          updateCourse({ title: event.target.value })
                        }
                      />
                    </label>
                    <label className="course-editor-field">
                      <span>Категория</span>
                      <input
                        value={selectedCourse.category || ""}
                        onChange={(event) =>
                          updateCourse({ category: event.target.value })
                        }
                      />
                    </label>
                    <label className="course-editor-field">
                      <span>Длительность</span>
                      <input
                        value={selectedCourse.duration || ""}
                        onChange={(event) =>
                          updateCourse({ duration: event.target.value })
                        }
                      />
                    </label>
                    <label className="course-editor-field">
                      <span>Уровень</span>
                      <input
                        value={selectedCourse.level || ""}
                        onChange={(event) =>
                          updateCourse({ level: event.target.value })
                        }
                      />
                    </label>
                    <label className="course-editor-field">
                      <span>Формат</span>
                      <input
                        value={selectedCourse.format || ""}
                        onChange={(event) =>
                          updateCourse({ format: event.target.value })
                        }
                      />
                    </label>
                    <label className="course-editor-field course-editor-field-wide">
                      <span>Описание</span>
                      <textarea
                        value={selectedCourse.description || ""}
                        onChange={(event) =>
                          updateCourse({ description: event.target.value })
                        }
                      />
                    </label>
                  </div>

                  <div className="course-objectives-editor">
                    <div className="course-objectives-editor-head">
                      <span>Цели курса</span>
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={addObjective}
                      >
                        Добавить цель
                      </button>
                    </div>
                    {learningObjectives.map((objective, index) => (
                      <div className="course-objective-row" key={index}>
                        <input
                          value={objective}
                          placeholder={`Цель ${index + 1}`}
                          onChange={(event) =>
                            updateObjective(index, event.target.value)
                          }
                        />
                        <button
                          type="button"
                          onClick={() => removeObjective(index)}
                        >
                          Удалить
                        </button>
                      </div>
                    ))}
                    {learningObjectives.length === 0 && (
                      <p className="course-objectives-empty">
                        Пока нет целей. Добавьте первую цель курса.
                      </p>
                    )}
                  </div>
                </div>
              )}

              {!isCourseEditMode && (
                <>
                  <p className="course-category">{selectedCourse.category}</p>
                  <p className="course-details-text">
                    {selectedCourse.description}
                  </p>
                  {selectedCourse.learningObjectives?.length > 0 && (
                    <div className="course-objectives-block">
                      <h3>Цели курса</h3>
                      <ul>
                        {selectedCourse.learningObjectives.map(
                          (objective, index) => (
                            <li key={`${selectedCourse.id}-objective-${index}`}>
                              {objective}
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}
                  <div className="course-stats-grid">
                    <div>
                      <span>Длительность</span>
                      <strong>{selectedCourse.duration}</strong>
                    </div>
                    <div>
                      <span>Объем</span>
                      <strong>{totalLessonsInCourse} уроков</strong>
                    </div>
                    <div>
                      <span>Уровень</span>
                      <strong>{selectedCourse.level}</strong>
                    </div>
                    <div>
                      <span>Формат</span>
                      <strong>{selectedCourse.format}</strong>
                    </div>
                  </div>
                </>
              )}
            </article>

            <article className="glass-card course-details-modules">
              <h3>Модули</h3>
              <ul className="course-blocks-list">
                {renderInsertControl(0)}
                {selectedCourse.blocks.map((block, index) => {
                  const isActive = activeBlockId === block.id;
                  const doneLessons = block.lessons.filter(
                    (lesson) => completedLessons[lesson.id],
                  ).length;
                  const donePractices = block.practice.filter(
                    (practice) => completedPractices[practice.id],
                  ).length;
                  const doneItems = doneLessons + donePractices;
                  const totalItems =
                    block.lessons.length + block.practice.length;

                  return (
                    <Fragment key={block.id}>
                      <li>
                        {isCourseEditMode ? (
                          <article className="course-block-item course-block-editor is-editing">
                            <span className="course-block-index">
                              {String(index + 1).padStart(2, "0")}
                            </span>
                            <div className="course-editor-grid">
                              <label className="course-editor-field">
                                <span>Название модуля</span>
                                <input
                                  value={block.title}
                                  onChange={(event) =>
                                    updateCourseBlock(block.id, {
                                      title: event.target.value,
                                    })
                                  }
                                />
                              </label>
                              <label className="course-editor-field">
                                <span>Длительность</span>
                                <input
                                  value={block.duration}
                                  onChange={(event) =>
                                    updateCourseBlock(block.id, {
                                      duration: event.target.value,
                                    })
                                  }
                                />
                              </label>
                              <label className="course-editor-field course-editor-field-wide">
                                <span>Описание</span>
                                <textarea
                                  value={block.description || ""}
                                  onChange={(event) =>
                                    updateCourseBlock(block.id, {
                                      description: event.target.value,
                                    })
                                  }
                                />
                              </label>
                            </div>
                            <div className="course-editor-actions">
                              <button
                                type="button"
                                className="btn btn-outline"
                                onClick={() => moveBlock(block.id, -1)}
                                disabled={index === 0}
                              >
                                Выше
                              </button>
                              <button
                                type="button"
                                className="btn btn-outline"
                                onClick={() => moveBlock(block.id, 1)}
                                disabled={
                                  index === selectedCourse.blocks.length - 1
                                }
                              >
                                Ниже
                              </button>
                              <button
                                type="button"
                                className="btn btn-solid"
                                onClick={() => openBlock(block.id)}
                              >
                                Перейти в модуль
                              </button>

                              <button
                                type="button"
                                className="btn btn-flat editor-danger-btn"
                                onClick={() =>
                                  setPendingDelete({
                                    type: "module",
                                    id: block.id,
                                    title: block.title,
                                  })
                                }
                                disabled={selectedCourse.blocks.length <= 1}
                              >
                                Удалить
                              </button>
                            </div>
                          </article>
                        ) : (
                          <button
                            type="button"
                            className={`course-block-item ${isActive ? "is-editing" : ""}`}
                            onClick={() =>
                              isCourseEditMode
                                ? setActiveBlockId((current) =>
                                    current === block.id ? null : block.id,
                                  )
                                : openBlock(block.id)
                            }
                          >
                            <span className="course-block-index">
                              {String(index + 1).padStart(2, "0")}
                            </span>
                            <span className="course-block-title">
                              {block.title}
                            </span>
                            {block.description && (
                              <span className="course-block-description">
                                {block.description}
                              </span>
                            )}
                            <span className="course-block-meta">
                              {block.duration} • {block.lessons.length} урока •{" "}
                              {block.practice.length} практики
                            </span>
                            <span className="course-block-progress">
                              Пройдено: {doneItems}/{totalItems}
                            </span>
                          </button>
                        )}
                      </li>
                      {renderInsertControl(index + 1)}
                    </Fragment>
                  );
                })}
              </ul>
            </article>

            {!isCourseEditMode && (
              <article className="glass-card course-leaderboard-card">
                <div className="course-leaderboard-head">
                  <h3>Лидерборд курса</h3>
                </div>
                <ol className="course-leaderboard-list">
                  {selectedCourseLeaderboard.map((student, index) => (
                    <li key={student.id}>
                      <span className="course-leaderboard-rank">
                        {index + 1}
                      </span>
                      <div className="course-leaderboard-main">
                        <strong>{student.name}</strong>
                        <small>{student.pace}</small>
                      </div>
                      <span className="course-leaderboard-score">
                        {student.progress}%
                      </span>
                    </li>
                  ))}
                </ol>
              </article>
            )}
          </div>
        </div>
      </div>

      {canGenerateModule && moduleAgentAt !== null && (
        <AgentInterviewDialog
          variant="floating"
          open={isModuleChatVisible}
          kind="module"
          courseId={selectedCourse.id}
          order={moduleAgentAt + 1}
          knownIds={selectedCourse.blocks.map((block) => block.id)}
          contextTitle={
            moduleJob?.resultId
              ? `Модуль «${moduleJob.resultTitle || "без названия"}» уже в списке.`
              : describeModulePosition(moduleAgentAt)
          }
          onClose={closeModuleAgent}
          onOpenResult={(job) => {
            setModuleAgentIndex(null);
            if (job.resultId) openBlock(job.resultId);
          }}
          onStartAnother={(job) => {
            // Следующий модуль — сразу после готового (order у job с единицы).
            const order = Number(job?.order);
            setModuleAgentIndex(
              Number.isFinite(order)
                ? Math.min(Math.max(order, 0), selectedCourse.blocks.length)
                : selectedCourse.blocks.length,
            );
            setIsModuleChatVisible(true);
          }}
        />
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        danger
        eyebrow="Необратимое действие"
        title={
          pendingDelete?.type === "course" ? "Удалить курс?" : "Удалить модуль?"
        }
        description={
          pendingDelete?.type === "course"
            ? `Курс «${pendingDelete?.title || ""}» будет перенесён в архив и пропадёт из каталога.`
            : `Модуль «${pendingDelete?.title || ""}» и все его уроки будут удалены. Отменить удаление нельзя.`
        }
        confirmLabel="Удалить"
        busyLabel="Удаляем..."
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          const target = pendingDelete;
          if (!target) return;
          if (target.type === "course") {
            setStatusAction("archive");
            try {
              await deleteCourse(target.id);
            } finally {
              setStatusAction("");
            }
          } else {
            const deleted = await deleteBlock(target.id);
            if (deleted === false) return false;
          }
          setPendingDelete(null);
        }}
      />
    </section>
  );
}
