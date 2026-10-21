// Страница выбранного блока курса с уроками и практикой
import { Fragment, useEffect, useState } from "react";
import SectionTop from "../components/SectionTop";
import CourseNavigationTree from "../components/CourseNavigationTree";
import AgentInterviewDialog, {
  resetAgentInterview,
} from "../components/editor/AgentInterviewDialog";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import { useGoBack } from "../hooks/useGoBack";
import {
  generationJobKey,
  useGenerationJobsStore,
} from "../stores/generationJobsStore";
import { isUuid } from "../utils/api";

export default function BlockPage({
  selectedCourse,
  selectedBlock,
  completedLessons,
  completedPractices,
  openBlock,
  openLesson,
  openPractice,
  isCourseEditMode,
  updateCourseBlock,
  addLessonToBlock,
  updateLesson,
  moveLesson,
  deleteLesson,
}) {
  const completedLessonsInBlock = selectedBlock.lessons.filter(
    (lesson) => completedLessons[lesson.id],
  ).length;
  const completedPracticesInBlock = selectedBlock.practice.filter(
    (practice) => completedPractices[practice.id],
  ).length;
  const totalItemsInBlock =
    selectedBlock.lessons.length + selectedBlock.practice.length;
  const completedInBlock = completedLessonsInBlock + completedPracticesInBlock;
  const blockProgressPercent = totalItemsInBlock
    ? Math.round((completedInBlock / totalItemsInBlock) * 100)
    : 0;
  const blockLearningObjectives = selectedBlock.learningObjectives || [];
  const [isAddingLesson, setIsAddingLesson] = useState(false);
  // Позиция в списке уроков, где открыт чат генерации урока (null — закрыт).
  const [lessonAgentIndex, setLessonAgentIndex] = useState(null);
  const [isLessonChatVisible, setIsLessonChatVisible] = useState(true);
  const [lessonToDelete, setLessonToDelete] = useState(null);
  const lessonJob = useGenerationJobsStore(
    (state) =>
      state.jobs[
        generationJobKey("lesson", selectedCourse.id, selectedBlock.id)
      ] || null,
  );
  // Перешли в другой модуль — место для урока выбирается заново.
  useEffect(() => {
    setLessonAgentIndex(null);
    setIsLessonChatVisible(true);
  }, [selectedBlock.id]);
  const canGenerateLesson =
    isCourseEditMode && isUuid(selectedCourse.id) && isUuid(selectedBlock.id);
  // Пока идёт генерация, чат остаётся в месте, куда вставится урок.
  const lessonAgentAt =
    lessonJob && Number.isFinite(Number(lessonJob.order))
      ? Number(lessonJob.order) - 1
      : lessonAgentIndex;

  const describeLessonPosition = (index) => {
    const lessons = selectedBlock.lessons;
    if (!lessons.length) return "Урок станет первым в модуле.";
    if (index <= 0)
      return `Урок встанет в начало, перед «${lessons[0].title}».`;
    if (index >= lessons.length) {
      return `Урок встанет в конец, после «${lessons[lessons.length - 1].title}».`;
    }
    return `Урок встанет между «${lessons[index - 1].title}» и «${lessons[index].title}».`;
  };

  const isLessonJobRunning = lessonJob?.status === "running";

  // Открывает чат у выбранного места или переносит туда уже открытый чат — окно не
  // закрывается. Пока генерация идёт, место менять нельзя. После готового или
  // упавшего запуска начинаем новый диалог.
  const openLessonAgent = (index) => {
    const currentJob =
      useGenerationJobsStore.getState().jobs[
        generationJobKey("lesson", selectedCourse.id, selectedBlock.id)
      ];
    if (currentJob?.status === "running") return;
    if (currentJob) {
      resetAgentInterview({
        kind: "lesson",
        courseId: selectedCourse.id,
        moduleId: selectedBlock.id,
      });
    }
    setLessonAgentIndex(index);
    setIsLessonChatVisible(true);
  };

  // Пока генерация идёт, окно только прячется: метка в списке остаётся.
  // Готовую или упавшую генерацию закрытие завершает — метка пропадает.
  const closeLessonAgent = () => {
    const currentJob =
      useGenerationJobsStore.getState().jobs[
        generationJobKey("lesson", selectedCourse.id, selectedBlock.id)
      ];
    if (currentJob?.status === "running") {
      setIsLessonChatVisible(false);
      return;
    }
    if (currentJob) {
      resetAgentInterview({
        kind: "lesson",
        courseId: selectedCourse.id,
        moduleId: selectedBlock.id,
      });
    }
    setLessonAgentIndex(null);
  };

  const renderLessonSlot = (index) => {
    if (!canGenerateLesson) return null;
    if (lessonAgentAt === index) {
      return (
        <li className="lesson-agent-marker" key={`lesson-agent-${index}`}>
          <span>
            {lessonJob?.status === "running"
              ? "✦ Здесь появится урок — генерация идёт"
              : lessonJob?.status === "done"
                ? "✦ Урок сгенерирован — ниже"
                : "✦ Сюда встанет урок из чата с ИИ"}
          </span>
          <div>
            {!isLessonChatVisible && (
              <button
                type="button"
                onClick={() => setIsLessonChatVisible(true)}
              >
                Показать чат
              </button>
            )}
            {!lessonJob && (
              <button type="button" onClick={() => setLessonAgentIndex(null)}>
                Отменить
              </button>
            )}
          </div>
        </li>
      );
    }
    return (
      <li className="lesson-insert-slot" key={`lesson-slot-${index}`}>
        <button
          type="button"
          className="is-ai"
          onClick={() => openLessonAgent(index)}
          disabled={isLessonJobRunning}
          title={
            isLessonJobRunning
              ? "Дождитесь окончания текущей генерации урока"
              : undefined
          }
        >
          {lessonAgentAt === null
            ? "✦ Сгенерировать урок с ИИ здесь"
            : "✦ Сгенерировать урок здесь"}
        </button>
      </li>
    );
  };
  const goBack = useGoBack({
    fallbackPath: isCourseEditMode
      ? `/course/${selectedCourse.id}/edit`
      : `/course/${selectedCourse.id}`,
  });

  const addLesson = async () => {
    if (!addLessonToBlock || isAddingLesson) return;

    setIsAddingLesson(true);
    try {
      const lessonId = await addLessonToBlock(selectedBlock.id);
      if (lessonId) {
        openLesson(lessonId);
      }
    } finally {
      setIsAddingLesson(false);
    }
  };

  const updateBlockObjective = (index, value) => {
    const nextObjectives = [...blockLearningObjectives];
    nextObjectives[index] = value;
    updateCourseBlock(selectedBlock.id, { learningObjectives: nextObjectives });
  };

  const addBlockObjective = () => {
    updateCourseBlock(selectedBlock.id, {
      learningObjectives: [...blockLearningObjectives, ""],
    });
  };

  const removeBlockObjective = (index) => {
    updateCourseBlock(selectedBlock.id, {
      learningObjectives: blockLearningObjectives.filter(
        (_, itemIndex) => itemIndex !== index,
      ),
    });
  };

  return (
    <section
      className={`container section block-view ${isCourseEditMode ? "is-course-edit-layout" : ""}`}
    >
      <SectionTop label="Блок" title={selectedBlock.title} />
      <button
        type="button"
        className="btn btn-outline back-btn"
        onClick={goBack}
        aria-label="Назад к курсу"
        title="Назад к курсу"
      >
        &lt;
      </button>
      {/* Та же сетка, что в режиме обучения: дерево курса слева, модуль справа. */}
      <div className="course-edit-grid">
        <CourseNavigationTree
          selectedCourse={selectedCourse}
          selectedBlock={selectedBlock}
          selectedLessonId=""
          selectedPracticeId=""
          completedLessons={completedLessons}
          completedPractices={completedPractices}
          openBlock={openBlock || (() => {})}
          openLesson={openLesson}
          openPractice={openPractice}
          mode="theory"
        />
        <div className="course-edit-main">
          <div className="block-view-grid">
            <article className="glass-card block-main-card">
              {!isCourseEditMode && (
                <>
                  <p className="course-category">{selectedCourse.title}</p>
                  <p className="course-details-text">
                    {selectedBlock.description ||
                      "Детальный блок курса с уроками и практикой. Используйте этот экран как тестовые данные для сценариев проваливания в контент."}
                  </p>
                  {selectedBlock.learningObjectives?.length > 0 && (
                    <div className="course-objectives-block">
                      <h3>Цели блока</h3>
                      <ul>
                        {selectedBlock.learningObjectives.map(
                          (objective, index) => (
                            <li key={`${selectedBlock.id}-objective-${index}`}>
                              {objective}
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}
                  <div className="block-progress-wrap">
                    <div className="block-progress-head">
                      <span>Прогресс блока</span>
                      <strong>
                        {completedInBlock}/{totalItemsInBlock} •{" "}
                        {blockProgressPercent}%
                      </strong>
                    </div>
                    <div className="block-progress-bar">
                      <div style={{ width: `${blockProgressPercent}%` }} />
                    </div>
                  </div>
                  <div className="course-stats-grid">
                    <div>
                      <span>Длительность блока</span>
                      <strong>{selectedBlock.duration}</strong>
                    </div>
                    <div>
                      <span>Уроков</span>
                      <strong>{selectedBlock.lessons.length}</strong>
                    </div>
                    <div>
                      <span>Практик</span>
                      <strong>{selectedBlock.practice.length}</strong>
                    </div>
                    <div>
                      <span>Тип</span>
                      <strong>Теория + практика</strong>
                    </div>
                  </div>
                </>
              )}
              {isCourseEditMode && (
                <div className="course-editor-panel block-editor-panel">
                  <div className="course-editor-grid">
                    <label className="course-editor-field">
                      <span>Название урока</span>
                      <input
                        value={selectedBlock.title || ""}
                        onChange={(event) =>
                          updateCourseBlock(selectedBlock.id, {
                            title: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label className="course-editor-field">
                      <span>Длительность</span>
                      <input
                        value={selectedBlock.duration || ""}
                        onChange={(event) =>
                          updateCourseBlock(selectedBlock.id, {
                            duration: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label className="course-editor-field course-editor-field-wide">
                      <span>Описание</span>
                      <textarea
                        value={selectedBlock.description || ""}
                        onChange={(event) =>
                          updateCourseBlock(selectedBlock.id, {
                            description: event.target.value,
                          })
                        }
                      />
                    </label>
                  </div>
                  <div className="course-objectives-editor">
                    <div className="course-objectives-editor-head">
                      <span>Цели урока</span>
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={addBlockObjective}
                      >
                        Добавить цель
                      </button>
                    </div>
                    {blockLearningObjectives.map((objective, index) => (
                      <div className="course-objective-row" key={index}>
                        <input
                          value={objective || ""}
                          placeholder={`Цель ${index + 1}`}
                          onChange={(event) =>
                            updateBlockObjective(index, event.target.value)
                          }
                        />
                        <button
                          type="button"
                          onClick={() => removeBlockObjective(index)}
                        >
                          Удалить
                        </button>
                      </div>
                    ))}
                    {blockLearningObjectives.length === 0 && (
                      <p className="course-objectives-empty">
                        Пока нет целей. Добавьте первую цель блока.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </article>

            <article className="glass-card block-lessons-card">
              <div className="block-lessons-head">
                <h3>Уроки</h3>
                {isCourseEditMode && (
                  <div className="block-lessons-actions">
                    {canGenerateLesson && lessonAgentAt === null && (
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={() =>
                          openLessonAgent(selectedBlock.lessons.length)
                        }
                      >
                        Сгенерировать урок с ИИ
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-solid"
                      onClick={addLesson}
                      disabled={isAddingLesson}
                    >
                      {isAddingLesson ? "Создаём урок..." : "Добавить урок"}
                    </button>
                  </div>
                )}
              </div>
              {selectedBlock.lessons.length === 0 && (
                <div className="course-editor-panel block-empty-lessons">
                  <h4>В этом модуле пока нет уроков</h4>
                  <p>
                    Создайте первый урок, чтобы наполнить модуль теорией и
                    материалами.
                  </p>
                  {isCourseEditMode && (
                    <button
                      type="button"
                      className="btn btn-solid"
                      onClick={addLesson}
                      disabled={isAddingLesson}
                    >
                      {isAddingLesson
                        ? "Создаём урок..."
                        : "Создать первый урок"}
                    </button>
                  )}
                </div>
              )}
              <ul className="lessons-progress-list">
                {selectedBlock.lessons.map((lesson, index) => (
                  <Fragment key={lesson.id}>
                    {renderLessonSlot(index)}
                    <li>
                      {isCourseEditMode ? (
                        <div className="course-editor-panel content-editor-panel lesson-basic-editor-panel">
                          <div className="lesson-content-editor-head">
                            <div>
                              <span>Урок {index + 1}</span>
                              <strong>
                                {lesson.title || "Урок без названия"}
                              </strong>
                            </div>
                          </div>
                          <div className="course-editor-grid">
                            <label className="course-editor-field">
                              <span>Название урока</span>
                              <input
                                value={lesson.title || ""}
                                onChange={(event) =>
                                  updateLesson(lesson.id, {
                                    title: event.target.value,
                                  })
                                }
                              />
                            </label>
                            <label className="course-editor-field">
                              <span>Длительность</span>
                              <input
                                value={lesson.duration || ""}
                                onChange={(event) =>
                                  updateLesson(lesson.id, {
                                    duration: event.target.value,
                                  })
                                }
                              />
                            </label>
                            <label className="course-editor-field course-editor-field-wide">
                              <span>Краткое описание</span>
                              <textarea
                                value={lesson.summary || ""}
                                onChange={(event) =>
                                  updateLesson(lesson.id, {
                                    summary: event.target.value,
                                  })
                                }
                              />
                            </label>
                          </div>
                          <div className="course-editor-actions">
                            <button
                              type="button"
                              className="btn btn-solid"
                              onClick={() => openLesson(lesson.id)}
                            >
                              Перейти в урок
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline"
                              onClick={() =>
                                moveLesson(selectedBlock.id, lesson.id, -1)
                              }
                              disabled={index === 0}
                            >
                              Выше
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline"
                              onClick={() =>
                                moveLesson(selectedBlock.id, lesson.id, 1)
                              }
                              disabled={
                                index === selectedBlock.lessons.length - 1
                              }
                            >
                              Ниже
                            </button>
                            <button
                              type="button"
                              className="btn btn-flat editor-danger-btn"
                              onClick={() => setLessonToDelete(lesson)}
                              disabled={selectedBlock.lessons.length <= 1}
                            >
                              Удалить
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="lesson-progress-item"
                          onClick={() => openLesson(lesson.id)}
                        >
                          <span className="lesson-progress-title">
                            {lesson.title}
                          </span>
                          <span className="lesson-progress-meta">
                            {lesson.duration}
                          </span>
                          <span
                            className={`lesson-status ${completedLessons[lesson.id] ? "is-done" : "is-pending"}`}
                          >
                            {completedLessons[lesson.id]
                              ? "Пройдено"
                              : "Не пройден"}
                          </span>
                        </button>
                      )}
                    </li>
                  </Fragment>
                ))}
                {renderLessonSlot(selectedBlock.lessons.length)}
              </ul>
            </article>

            {!isCourseEditMode && (
              <article className="glass-card block-practice-card">
                <h3>Практика и задания</h3>
                <ul className="practice-progress-list">
                  {selectedBlock.practice.map((task) => (
                    <li key={task.id}>
                      <button
                        type="button"
                        className="practice-progress-item"
                        onClick={() => openPractice(task.id)}
                      >
                        <span className="practice-progress-title">
                          {task.title}
                        </span>
                        <span className="practice-progress-meta">
                          {task.duration}
                        </span>
                        <span
                          className={`practice-status ${completedPractices[task.id] ? "is-done" : "is-pending"}`}
                        >
                          {completedPractices[task.id]
                            ? "Выполнено"
                            : "Не выполнено"}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </article>
            )}
          </div>
        </div>
      </div>

      {canGenerateLesson && lessonAgentAt !== null && (
        <AgentInterviewDialog
          variant="floating"
          open={isLessonChatVisible}
          kind="lesson"
          courseId={selectedCourse.id}
          moduleId={selectedBlock.id}
          order={lessonAgentAt + 1}
          knownIds={selectedBlock.lessons.map((lesson) => lesson.id)}
          contextTitle={
            lessonJob?.resultId
              ? `Урок «${lessonJob.resultTitle || "без названия"}» уже в списке.`
              : `Модуль «${selectedBlock.title}». ${describeLessonPosition(lessonAgentAt)}`
          }
          onClose={closeLessonAgent}
          onOpenResult={(job) => {
            setLessonAgentIndex(null);
            if (job.resultId) openLesson(job.resultId);
          }}
          onStartAnother={(job) => {
            // Следующий урок — сразу после готового (order у job с единицы).
            const order = Number(job?.order);
            setLessonAgentIndex(
              Number.isFinite(order)
                ? Math.min(Math.max(order, 0), selectedBlock.lessons.length)
                : selectedBlock.lessons.length,
            );
            setIsLessonChatVisible(true);
          }}
        />
      )}

      <ConfirmDialog
        open={Boolean(lessonToDelete)}
        danger
        eyebrow="Необратимое действие"
        title="Удалить урок?"
        description={`Урок «${lessonToDelete?.title || ""}» и его содержимое будут удалены. Отменить удаление нельзя.`}
        confirmLabel="Удалить"
        busyLabel="Удаляем..."
        onCancel={() => setLessonToDelete(null)}
        onConfirm={async () => {
          if (!lessonToDelete) return;
          await deleteLesson(selectedBlock.id, lessonToDelete.id);
          setLessonToDelete(null);
        }}
      />
    </section>
  );
}
