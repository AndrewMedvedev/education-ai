import { useEffect, useMemo } from "react";
import { useCourseMetricsStore } from "../../stores/courseMetricsStore";

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Number(totalSeconds) || 0);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const restSeconds = seconds % 60;

  if (hours > 0) return `${hours} ч ${minutes} мин`;
  if (minutes > 0) return `${minutes} мин ${restSeconds} сек`;
  return `${restSeconds} сек`;
}

function formatChartScale(seconds) {
  if (seconds >= 60) {
    const minutes = seconds / 60;
    return Number.isInteger(minutes)
      ? `${minutes} мин`
      : `${minutes.toFixed(1)} мин`;
  }
  return `${seconds} сек`;
}

function getActiveTimeTone(seconds) {
  if ((Number(seconds) || 0) < 60) return "is-danger";
  if ((Number(seconds) || 0) < 300) return "is-warning";
  return "is-good";
}

function getScrollTone(percent) {
  const value = Number(percent) || 0;
  if (value < 30) return "is-danger";
  if (value < 60) return "is-warning";
  return "is-good";
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getInitials(name) {
  return (
    String(name || "Студент")
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "С"
  );
}

function StudentName({ user, isLoading, error }) {
  if (user?.fullName) {
    return (
      <>
        <strong>{user.fullName}</strong>
        <small>{user.email || "Профиль загружен"}</small>
      </>
    );
  }

  if (isLoading) {
    return (
      <>
        <strong className="metrics-skeleton">Загружаем ФИО</strong>
        <small className="metrics-skeleton metrics-skeleton-short">
          Профиль
        </small>
      </>
    );
  }

  return (
    <>
      <strong>{error ? "Профиль недоступен" : "ФИО не указано"}</strong>
      <small>{error || "Ожидаем fullName из профиля"}</small>
    </>
  );
}

export default function LessonMetricsDashboard({ courseId, lesson }) {
  const students = useCourseMetricsStore((state) => state.students);
  const studentsMeta = useCourseMetricsStore((state) => state.studentsMeta);
  const isStudentsLoading = useCourseMetricsStore(
    (state) => state.isStudentsLoading,
  );
  const studentsError = useCourseMetricsStore((state) => state.studentsError);
  const usersCache = useCourseMetricsStore((state) => state.usersCache);
  const usersLoading = useCourseMetricsStore((state) => state.usersLoading);
  const usersErrors = useCourseMetricsStore((state) => state.usersErrors);
  const selectedStudentUserId = useCourseMetricsStore(
    (state) => state.selectedStudentUserId,
  );
  const sessions = useCourseMetricsStore((state) => state.sessions);
  const sessionsFilters = useCourseMetricsStore(
    (state) => state.sessionsFilters,
  );
  const isSessionsLoading = useCourseMetricsStore(
    (state) => state.isSessionsLoading,
  );
  const sessionsError = useCourseMetricsStore((state) => state.sessionsError);
  const setSelectedStudent = useCourseMetricsStore(
    (state) => state.setSelectedStudent,
  );
  const resetSelectionAndSessions = useCourseMetricsStore(
    (state) => state.resetSelectionAndSessions,
  );
  const setFilters = useCourseMetricsStore((state) => state.setFilters);
  const loadStudents = useCourseMetricsStore((state) => state.loadStudents);
  const loadSessions = useCourseMetricsStore((state) => state.loadSessions);

  const lessonId = lesson?.id || "";
  const isDateRangeInvalid = Boolean(
    sessionsFilters.dateFrom &&
    sessionsFilters.dateTo &&
    sessionsFilters.dateFrom > sessionsFilters.dateTo,
  );

  useEffect(() => {
    resetSelectionAndSessions();
  }, [lessonId, resetSelectionAndSessions]);

  useEffect(() => {
    if (!courseId || !lessonId) return undefined;
    const pageSize = studentsMeta.size || 10;
    loadStudents(courseId, { page: 1, size: pageSize }).catch(() => null);
    return undefined;
  }, [courseId, lessonId, loadStudents]);

  useEffect(() => {
    if (!lessonId || !selectedStudentUserId || isDateRangeInvalid) return;
    loadSessions(lessonId, selectedStudentUserId).catch(() => null);
  }, [
    isDateRangeInvalid,
    lessonId,
    loadSessions,
    selectedStudentUserId,
    sessionsFilters.createdFrom,
    sessionsFilters.createdTo,
    sessionsFilters.sort,
  ]);

  const selectedUser = selectedStudentUserId
    ? usersCache[selectedStudentUserId]
    : null;

  const summary = useMemo(() => {
    const completedCount = sessions.filter(
      (session) => session.completedAt,
    ).length;
    const maxActive = Math.max(
      1,
      ...sessions.map((session) => session.activeTimeSeconds || 0),
    );
    const chartScaleMax = Math.max(60, Math.ceil(maxActive / 60) * 60);
    const chartScaleMiddle = Math.round(chartScaleMax / 2);

    return { chartScaleMax, chartScaleMiddle };
  }, [sessions]);

  const changeStudentsPage = (page) => {
    const nextPage = Math.min(Math.max(1, page), studentsMeta.pages || 1);
    loadStudents(courseId, {
      page: nextPage,
      size: studentsMeta.size || 10,
    }).catch(() => null);
  };

  const selectStudent = (userId) => {
    setSelectedStudent(userId);
  };

  const updateFilter = (field, value) => {
    setFilters({ [field]: value });
  };

  return (
    <div className="lesson-metrics-dashboard">
      <div className="metrics-dashboard-head">
        <div>
          <span className="metrics-mode-badge">Режим метрик</span>
          <h2>Метрики прохождения теории</h2>
          <p>{lesson?.title || "Выберите урок в дереве курса"}</p>
        </div>
      </div>

      <div className="metrics-workspace">
        <aside className="metrics-students-panel">
          <div className="metrics-panel-head">
            <div>
              <h3>Студенты курса</h3>
              <p>Выберите студента для просмотра метрик этого урока.</p>
            </div>
          </div>

          {studentsError && (
            <p className="lesson-ai-error" role="alert">
              {studentsError}
            </p>
          )}
          {isStudentsLoading && (
            <p className="course-viewer-muted">Загружаем студентов...</p>
          )}
          {!isStudentsLoading && !studentsError && students.length === 0 && (
            <p className="metrics-empty-state">
              На курс пока не записаны студенты.
            </p>
          )}

          <ul className="metrics-student-list">
            {students.map((student) => {
              const user = usersCache[student.userId];
              const isUserLoading = usersLoading[student.userId];
              const userError = usersErrors[student.userId];
              const displayName = user?.fullName || "ФИО";
              return (
                <li key={student.id || student.userId}>
                  <button
                    type="button"
                    className={`metrics-student-btn ${selectedStudentUserId === student.userId ? "is-active" : ""}`}
                    onClick={() => selectStudent(student.userId)}
                  >
                    <span className="metrics-student-avatar">
                      {user?.avatarUrl ? (
                        <img src={user.avatarUrl} alt="" />
                      ) : (
                        getInitials(displayName)
                      )}
                    </span>
                    <span className="metrics-student-main">
                      <StudentName
                        user={user}
                        isLoading={isUserLoading}
                        error={userError}
                      />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          {studentsMeta.pages > 1 && (
            <nav
              className="metrics-pagination"
              aria-label="Пагинация студентов"
            >
              <span>
                {studentsMeta.page} / {studentsMeta.pages}
              </span>
              <div>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => changeStudentsPage(studentsMeta.page - 1)}
                  disabled={!studentsMeta.has_prev || isStudentsLoading}
                >
                  Назад
                </button>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => changeStudentsPage(studentsMeta.page + 1)}
                  disabled={!studentsMeta.has_next || isStudentsLoading}
                >
                  Вперёд
                </button>
              </div>
            </nav>
          )}
        </aside>

        <section className="metrics-dashboard-panel">
          <div className="metrics-filters-card">
            <div>
              <h3>
                {selectedUser?.fullName ||
                  (selectedStudentUserId
                    ? "ФИО не указано"
                    : "Студент не выбран")}
              </h3>
              <p>
                Период фильтрует сессии по дате создания: начало дня
                включительно, конечная дата — до начала следующего дня.
              </p>
            </div>
            <div className="metrics-date-filters">
              <label>
                <span>С даты</span>
                <input
                  type="date"
                  value={sessionsFilters.dateFrom}
                  onChange={(event) =>
                    updateFilter("dateFrom", event.target.value)
                  }
                  disabled={!selectedStudentUserId}
                />
              </label>
              <label>
                <span>По дату</span>
                <input
                  type="date"
                  value={sessionsFilters.dateTo}
                  onChange={(event) =>
                    updateFilter("dateTo", event.target.value)
                  }
                  disabled={!selectedStudentUserId}
                />
              </label>
            </div>
          </div>

          {!selectedStudentUserId ? (
            <div className="metrics-empty-state metrics-empty-state-large">
              Выберите студента слева — после этого загрузятся графики по
              текущему уроку.
            </div>
          ) : isDateRangeInvalid ? (
            <div className="lesson-ai-error" role="alert">
              Дата начала периода не должна быть позже даты окончания.
            </div>
          ) : sessionsError ? (
            <div className="lesson-ai-error" role="alert">
              {sessionsError}
            </div>
          ) : isSessionsLoading ? (
            <div className="metrics-empty-state metrics-empty-state-large">
              Загружаем метрики...
            </div>
          ) : sessions.length === 0 ? (
            <div className="metrics-empty-state metrics-empty-state-large">
              За выбранный период сессий теории не найдено.
            </div>
          ) : (
            <>
              <div className="metrics-chart-card">
                <div className="metrics-chart-head">
                  <div>
                    <h3>Активное время по сессиям</h3>
                    <p>Высота столбца показывает активное время в сессии.</p>
                  </div>
                  <div className="metrics-chart-legend">
                    <span className="is-danger">&lt; 1 мин</span>
                    <span className="is-warning">1–5 мин</span>
                    <span className="is-good">5+ мин</span>
                  </div>
                </div>
                <div className="metrics-chart-with-axis">
                  <div className="metrics-y-axis" aria-hidden="true">
                    <span>{formatChartScale(summary.chartScaleMax)}</span>
                    <span>{formatChartScale(summary.chartScaleMiddle)}</span>
                    <span>0 сек</span>
                  </div>
                  <div className="metrics-bar-chart">
                    {sessions.map((session, index) => {
                      const activeSeconds = session.activeTimeSeconds || 0;
                      return (
                        <div
                          className="metrics-bar-column"
                          key={session.id || `${session.createdAt}-${index}`}
                        >
                          <div
                            className={`metrics-bar-value ${getActiveTimeTone(activeSeconds)}`}
                          >
                            {formatDuration(activeSeconds)}
                          </div>
                          <div
                            className={`metrics-bar ${getActiveTimeTone(activeSeconds)}`}
                            style={{
                              height: `${Math.max(3, Math.round((activeSeconds / summary.chartScaleMax) * 100))}%`,
                            }}
                            title={`${formatDuration(activeSeconds)} • ${formatDateTime(session.createdAt)}`}
                          />
                          <small>{formatDateTime(session.createdAt)}</small>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="metrics-session-list-card">
                <div className="metrics-chart-head">
                  <div>
                    <h3>Глубина скролла и статус</h3>
                    <p>
                      Цвет показывает глубину просмотра: красный — низкая,
                      жёлтый — средняя, зелёный — высокая.
                    </p>
                  </div>
                </div>
                <ul className="metrics-session-list">
                  {sessions.map((session, index) => (
                    <li key={session.id || `${session.createdAt}-row-${index}`}>
                      <div className="metrics-session-row-head">
                        <strong>{formatDateTime(session.createdAt)}</strong>
                        <span
                          className={
                            session.completedAt
                              ? "is-completed"
                              : "is-incomplete"
                          }
                        >
                          {session.completedAt ? "Завершена" : "Не завершена"}
                        </span>
                      </div>
                      <div
                        className={`metrics-progress-line ${getScrollTone(session.maxScrollDepthPercent || 0)}`}
                        aria-label={`Глубина скролла ${session.maxScrollDepthPercent}%`}
                      >
                        <div
                          style={{
                            width: `${Math.min(100, Math.max(0, session.maxScrollDepthPercent || 0))}%`,
                          }}
                        />
                      </div>
                      <small>
                        Просмотрено{" "}
                        {Math.round(session.maxScrollDepthPercent || 0)}% •
                        активное время{" "}
                        {formatDuration(session.activeTimeSeconds)}
                      </small>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
