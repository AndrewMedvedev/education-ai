// Страница выбранного блока курса с уроками и практикой
import { useState } from "react";
import SectionTop from "../components/SectionTop";
import { useGoBack } from "../hooks/useGoBack";

export default function BlockPage({
  selectedCourse,
  selectedBlock,
  completedLessons,
  completedPractices,
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
              <button
                type="button"
                className="btn btn-solid"
                onClick={addLesson}
                disabled={isAddingLesson}
              >
                {isAddingLesson ? "Создаём урок..." : "Добавить урок"}
              </button>
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
                  {isAddingLesson ? "Создаём урок..." : "Создать первый урок"}
                </button>
              )}
            </div>
          )}
          <ul className="lessons-progress-list">
            {selectedBlock.lessons.map((lesson, index) => (
              <li key={lesson.id}>
                {isCourseEditMode ? (
                  <div className="course-editor-panel content-editor-panel lesson-basic-editor-panel">
                    <div className="lesson-content-editor-head">
                      <div>
                        <span>Урок {index + 1}</span>
                        <strong>{lesson.title || "Урок без названия"}</strong>
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
                        disabled={index === selectedBlock.lessons.length - 1}
                      >
                        Ниже
                      </button>
                      <button
                        type="button"
                        className="btn btn-flat editor-danger-btn"
                        onClick={() =>
                          deleteLesson(selectedBlock.id, lesson.id)
                        }
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
                      {completedLessons[lesson.id] ? "Пройдено" : "Не пройден"}
                    </span>
                  </button>
                )}
              </li>
            ))}
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
    </section>
  );
}
