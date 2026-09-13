// Страница деталей выбранного курса с описанием, блоками и лидербордом
import { Fragment, useState } from "react";
import SectionTop from "../components/SectionTop";
import { useGoBack } from "../hooks/useGoBack";

export default function CoursePage({
  selectedCourse,
  selectedCourseLeaderboard,
  completedLessons,
  completedPractices,
  openBlock,
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

  const renderInsertControl = (index) =>
    isCourseEditMode ? (
      <li className="course-block-insert" key={`insert-${index}`}>
        <button type="button" onClick={() => insertBlock(index)}>
          Вставить здесь
        </button>
      </li>
    ) : null;

  return (
    <section className="container section course-details-view">
      <SectionTop label="Курс" title={selectedCourse.title} />
      <button
        type="button"
        className="btn btn-outline back-btn"
        onClick={goBack}
        aria-label="Назад к каталогу"
        title="Назад к каталогу"
      >
        &lt;
      </button>
      <div className="course-page-actions">
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
                  {statusAction === "publish" ? "Публикуем..." : "Опубликовать"}
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
              onClick={async () => {
                if (statusAction) return;
                setStatusAction("archive");
                try {
                  await deleteCourse(selectedCourse.id);
                } finally {
                  setStatusAction("");
                }
              }}
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
              const totalItems = block.lessons.length + block.practice.length;

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
                            onClick={() => deleteBlock(block.id)}
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
                  <span className="course-leaderboard-rank">{index + 1}</span>
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
    </section>
  );
}
