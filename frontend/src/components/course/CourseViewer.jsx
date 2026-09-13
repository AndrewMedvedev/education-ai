import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  LessonPracticeAgent,
  LessonTestAgent,
} from "../LessonAgentAssessments";
import LessonChatWorkspace from "../LessonChatWorkspace";
import CourseNavigationTree from "../CourseNavigationTree";
import SectionTop from "../SectionTop";
import {
  getCourseBasicInfo,
  getCourseLearningStructure,
  getLessonById,
  getLessonContentBlocks,
  getModuleById,
} from "../../services/courseService";
import ContentBlocks from "./ContentBlocks";
import CourseBasicInfo from "./CourseBasicInfo";
import LessonBasicInfo from "./LessonBasicInfo";
import LessonList from "./LessonList";
import ModuleBasicInfo from "./ModuleBasicInfo";
import {
  COURSE_PERMISSIONS,
  usePermissionStore,
} from "../../stores/permissionStore";
import { useSessionStore } from "../../stores/sessionStore";
import { useStudentStore } from "../../stores/studentStore";
import { useUiLayoutStore } from "../../stores/uiLayoutStore";
import { useTheorySessionTracker } from "../../hooks/useTheorySessionTracker";
import { getErrorMessage } from "../../utils/errors";
import { isTokenExpired, isUuid } from "../../utils/api";
import ModuleList from "./ModuleList";
import LessonMetricsDashboard from "./LessonMetricsDashboard";
import "./course-viewer.css";

function findBlockByLesson(course, lessonId) {
  return (
    course?.blocks?.find((block) =>
      block.lessons.some((lesson) => lesson.id === lessonId),
    ) ?? null
  );
}

function toModuleBasicInfoFromLearningBlock(block) {
  if (!block) {
    return null;
  }

  const learningObjectives = Array.isArray(block.learningObjectives)
    ? block.learningObjectives
    : Array.isArray(block.learning_objectives)
      ? block.learning_objectives
      : [];

  return {
    id: block.id,
    title: block.title,
    description: block.description || "",
    order: Number.isFinite(block.order) ? block.order : 0,
    learning_objectives: learningObjectives,
    learningObjectives,
    lessons: (block.lessons || []).map((lesson, lessonIndex) => ({
      id: lesson.id,
      title: lesson.title,
      order: Number.isFinite(lesson.order) ? lesson.order : lessonIndex,
    })),
  };
}

function toLessonBasicInfoFromLearningLesson(lesson) {
  if (!lesson) {
    return null;
  }

  const estimatedTimeMatch = /^([0-9]+)\s*мин\.?$/i.exec(lesson.duration || "");
  const learningObjectives = Array.isArray(lesson.learningObjectives)
    ? lesson.learningObjectives
    : Array.isArray(lesson.learning_objectives)
      ? lesson.learning_objectives
      : [];

  return {
    id: lesson.id,
    title: lesson.title,
    description: lesson.summary || lesson.description || lesson.content || "",
    order: Number.isFinite(lesson.order) ? lesson.order : 0,
    learning_objectives: learningObjectives,
    learningObjectives,
    estimated_time_minutes: estimatedTimeMatch
      ? Number(estimatedTimeMatch[1])
      : null,
  };
}

export default function CourseViewer({ localCourse = null, mode = "view" }) {
  const { courseId, blockId, lessonId } = useParams();
  const navigate = useNavigate();
  const accessToken = useSessionStore((state) => state.accessToken);
  const refreshToken = useSessionStore((state) => state.refreshToken);
  const expiresAt = useSessionStore((state) => state.expiresAt);
  const identity = useSessionStore((state) => state.identity);
  const user = useSessionStore((state) => state.user);
  const isAuthenticated = Boolean(
    accessToken && expiresAt && (!isTokenExpired(expiresAt) || refreshToken),
  );
  const hasCourseInfoPermission = usePermissionStore((state) =>
    state.hasAnyPermission([
      COURSE_PERMISSIONS.READ,
      COURSE_PERMISSIONS.COURSE_READ,
    ]),
  );
  const canViewCourseInfo = !isAuthenticated || hasCourseInfoPermission;
  const canReadCourseContent = usePermissionStore((state) =>
    state.hasPermission(COURSE_PERMISSIONS.COURSE_READ),
  );
  const canUpdateCourse = usePermissionStore((state) =>
    state.hasPermission(COURSE_PERMISSIONS.UPDATE),
  );
  const [course, setCourse] = useState(null);
  const [selectedModuleId, setSelectedModuleId] = useState(blockId ?? null);
  const [selectedLessonId, setSelectedLessonId] = useState(lessonId ?? null);
  const [isLearningStarted, setIsLearningStarted] = useState(
    Boolean(blockId || lessonId),
  );
  const [contentBlocks, setContentBlocks] = useState([]);
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [enrollmentError, setEnrollmentError] = useState("");
  const theoryContainerRef = useRef(null);
  const theoryContentRef = useRef(null);
  const [isLoadingCourse, setIsLoadingCourse] = useState(true);
  const [isLoadingLesson, setIsLoadingLesson] = useState(false);
  const [error, setError] = useState(null);
  const effectiveCourseId = courseId || "";
  const isMetricsMode = mode === "metrics";
  const signCourse = useStudentStore((state) => state.signCourse);
  const loadMyCourses = useStudentStore((state) => state.loadMyCourses);
  const isCourseEnrolled = useStudentStore((state) => state.isCourseEnrolled);
  const isCourseSigning = useStudentStore((state) =>
    state.isCourseSigning(course?.id || effectiveCourseId),
  );
  const currentUserId =
    identity?.id ||
    identity?.user_id ||
    identity?.userId ||
    user?.id ||
    user?.user_id;
  const courseCreatorId =
    course?.creator_id ||
    course?.creatorId ||
    course?.author_id ||
    course?.authorId ||
    course?.user_id ||
    course?.userId;
  const isOwnCourse = Boolean(
    currentUserId && courseCreatorId && currentUserId === courseCreatorId,
  );
  const canViewWithoutEnrollment = isOwnCourse;
  const canNavigateCourseContent = isMetricsMode
    ? canUpdateCourse
    : canReadCourseContent;

  const selectedBlock = useMemo(() => {
    if (!course) {
      return null;
    }

    return (
      course.blocks.find((block) => block.id === selectedModuleId) ??
      findBlockByLesson(course, selectedLessonId) ??
      null
    );
  }, [course, selectedLessonId, selectedModuleId]);

  const selectedLesson = useMemo(() => {
    if (!selectedBlock || !selectedLessonId) {
      return null;
    }

    return (
      selectedBlock.lessons.find((lesson) => lesson.id === selectedLessonId) ??
      null
    );
  }, [selectedBlock, selectedLessonId]);

  const moduleBasicInfo = useMemo(
    () => toModuleBasicInfoFromLearningBlock(selectedBlock),
    [selectedBlock],
  );

  const lessonBasicInfo = useMemo(
    () => toLessonBasicInfoFromLearningLesson(selectedLesson),
    [selectedLesson],
  );

  const activeTab = useUiLayoutStore((state) =>
    state.getLessonActiveTab(selectedLesson?.id),
  );
  const setLessonActiveTab = useUiLayoutStore(
    (state) => state.setLessonActiveTab,
  );

  const shouldTrackTheorySession =
    mode === "view" &&
    canReadCourseContent &&
    (isEnrolled || isOwnCourse) &&
    activeTab === "theory";

  useTheorySessionTracker(selectedLesson?.id, {
    enabled: shouldTrackTheorySession,
    scrollContainerRef: theoryContainerRef,
    contentRef: theoryContentRef,
    isContentReady: !isLoadingLesson && !error,
  });

  useEffect(() => {
    let isMounted = true;

    async function loadCourse() {
      setIsLoadingCourse(true);
      setError(null);

      try {
        if (!effectiveCourseId) {
          throw new Error("Идентификатор курса не указан");
        }

        const basicCourse = isMetricsMode
          ? await getCourseLearningStructure(effectiveCourseId)
          : !isUuid(effectiveCourseId) && localCourse?.id === effectiveCourseId
            ? localCourse
            : await getCourseBasicInfo(effectiveCourseId);

        if (!isMetricsMode && canReadCourseContent) {
          await loadMyCourses({ page: 1, size: 100 }).catch(() => null);
        }

        const enrolled = canReadCourseContent
          ? useStudentStore.getState().isCourseEnrolled(basicCourse.id) ||
            (basicCourse.students || []).some(
              (student) => student?.course_id === basicCourse.id,
            )
          : false;

        if (!isMounted) {
          return;
        }

        setCourse(basicCourse);
        setIsEnrolled(enrolled);
        setSelectedModuleId(blockId ?? null);
        setSelectedLessonId(lessonId ?? null);
        setIsLearningStarted(
          isMetricsMode ||
            (Boolean(blockId || lessonId) && canReadCourseContent),
        );
      } catch (loadError) {
        if (isMounted) {
          setError(loadError.message || "Не удалось загрузить курс");
        }
      } finally {
        if (isMounted) {
          setIsLoadingCourse(false);
        }
      }
    }

    loadCourse();

    return () => {
      isMounted = false;
    };
  }, [
    blockId,
    canReadCourseContent,
    effectiveCourseId,
    isMetricsMode,
    lessonId,
    loadMyCourses,
    localCourse,
  ]);

  useEffect(() => {
    if (isMetricsMode || !canReadCourseContent || !selectedLesson?.id) {
      setContentBlocks([]);
      return;
    }

    let isMounted = true;

    async function loadLessonContent() {
      setIsLoadingLesson(true);
      setError(null);

      try {
        const lessonBlocks = await getLessonContentBlocks(selectedLesson.id);

        if (isMounted) {
          setContentBlocks(lessonBlocks);
        }
      } catch (loadError) {
        if (isMounted) {
          setError(loadError.message || "Не удалось загрузить теорию урока");
        }
      } finally {
        if (isMounted) {
          setIsLoadingLesson(false);
        }
      }
    }

    loadLessonContent();

    return () => {
      isMounted = false;
    };
  }, [canReadCourseContent, isMetricsMode, selectedLesson?.id]);

  const openCourseOverview = () => {
    if (!canNavigateCourseContent) {
      return;
    }

    setIsLearningStarted(true);
    setSelectedModuleId(null);
    setSelectedLessonId(null);
    navigate(
      isMetricsMode ? `/course/${course.id}/metrics` : `/course/${course.id}`,
    );
  };

  const startLearning = () => {
    if (!canReadCourseContent) {
      return;
    }

    setIsLearningStarted(true);
    setSelectedModuleId(null);
    setSelectedLessonId(null);
  };

  const openBlock = async (blockId) => {
    if (!canNavigateCourseContent) {
      return;
    }

    const fallbackBlock = course?.blocks.find((block) => block.id === blockId);
    setSelectedModuleId(blockId);
    setSelectedLessonId(null);
    setContentBlocks([]);
    setError(null);

    try {
      const nextBlock = isUuid(blockId)
        ? await getModuleById(blockId)
        : fallbackBlock;
      if (!nextBlock) {
        throw new Error("Модуль не найден");
      }
      setCourse((currentCourse) => {
        if (!currentCourse) return currentCourse;
        return {
          ...currentCourse,
          blocks: currentCourse.blocks.map((block) =>
            block.id === nextBlock.id ? { ...block, ...nextBlock } : block,
          ),
        };
      });
      navigate(
        isMetricsMode
          ? `/course/${course.id}/metrics`
          : `/course/${course.id}/block/${nextBlock.id || blockId}`,
      );
    } catch (loadError) {
      setSelectedModuleId(fallbackBlock?.id ?? null);
      setError(loadError.message || "Не удалось загрузить модуль");
    }
  };

  const openLesson = async (nextLessonId) => {
    if (!canNavigateCourseContent) {
      return;
    }

    const fallbackBlock = findBlockByLesson(course, nextLessonId);
    setSelectedModuleId(fallbackBlock?.id ?? selectedModuleId);
    setSelectedLessonId(nextLessonId);
    setContentBlocks([]);
    setError(null);

    try {
      const fallbackLesson = fallbackBlock?.lessons.find(
        (lesson) => lesson.id === nextLessonId,
      );
      const nextLesson = isUuid(nextLessonId)
        ? await getLessonById(nextLessonId)
        : fallbackLesson;
      if (!nextLesson) {
        throw new Error("Урок не найден");
      }
      setCourse((currentCourse) => {
        if (!currentCourse) return currentCourse;
        return {
          ...currentCourse,
          blocks: currentCourse.blocks.map((block) => ({
            ...block,
            lessons: block.lessons.map((lesson) =>
              lesson.id === nextLesson.id
                ? { ...lesson, ...nextLesson }
                : lesson,
            ),
          })),
        };
      });
      navigate(
        isMetricsMode
          ? `/course/${course.id}/metrics/lessons/${nextLessonId}`
          : `/course/${course.id}/lesson/${nextLessonId}`,
      );
    } catch (loadError) {
      setError(loadError.message || "Не удалось загрузить урок");
    }
  };

  const openCourseEditor = () => {
    if (course?.id && canUpdateCourse) {
      navigate(`/course/${course.id}/edit`);
    }
  };

  const openCourseMetrics = () => {
    if (course?.id && canUpdateCourse) {
      navigate(`/course/${course.id}/metrics`);
    }
  };

  const enrollToCourse = async () => {
    if (!course?.id || isCourseSigning) {
      return;
    }

    setEnrollmentError("");
    try {
      const student = await signCourse(course.id);
      setCourse((currentCourse) =>
        currentCourse
          ? {
              ...currentCourse,
              students: [...(currentCourse.students || []), student],
            }
          : currentCourse,
      );
      setIsEnrolled(true);
      setIsLearningStarted(true);
    } catch (error) {
      setEnrollmentError(
        getErrorMessage(error, "Не удалось записаться на курс."),
      );
    }
  };

  if (!canViewCourseInfo && !isMetricsMode) {
    return (
      <section className="container section course-viewer">
        <SectionTop label="Курс" title="Доступ ограничен" />
        <article className="glass-card course-viewer-error">
          Курс недоступен для вашей роли. Обратитесь к администратору
          организации, чтобы получить доступ.
        </article>
      </section>
    );
  }

  if (isLoadingCourse) {
    return (
      <section className="container section course-viewer">
        <article className="glass-card course-viewer-loading-card">
          <p className="course-viewer-muted">Загружаем курс...</p>
        </article>
      </section>
    );
  }

  if (error && !course) {
    return (
      <section className="container section course-viewer">
        <article className="glass-card course-viewer-error">
          <h1>Не удалось открыть курс</h1>
          <p>{error}</p>
        </article>
      </section>
    );
  }

  if (isMetricsMode && !canUpdateCourse) {
    return (
      <section className="container section course-viewer course-enrollment-view">
        <SectionTop label="Метрики курса" title="Доступ ограничен" />
        <article className="glass-card course-viewer-error">
          Для просмотра метрик нужны права управления курсом.
        </article>
      </section>
    );
  }

  if (!isMetricsMode && !canReadCourseContent) {
    return (
      <section className="container section course-viewer course-enrollment-view">
        <SectionTop label="Курс" title={course?.title || "Просмотр курса"} />
        {error && (
          <article className="glass-card course-viewer-error" role="alert">
            {error}
          </article>
        )}
        <CourseBasicInfo course={course} />
        <article className="glass-card locked-course-card generated-course-enroll-card">
          <div>
            <h2>Прохождение курса недоступно</h2>
            <p>
              {isAuthenticated
                ? "Вы можете смотреть информацию о курсе, но для открытия модулей, уроков, теории, практики и ИИ-ментора нужны дополнительные права."
                : "Вы можете смотреть информацию о курсе без авторизации. Войдите, чтобы получить доступ к прохождению курса."}
            </p>
          </div>
          {(!isAuthenticated || canUpdateCourse) && (
            <div className="generated-course-actions">
              {!isAuthenticated && (
                <button
                  type="button"
                  className="btn btn-solid"
                  onClick={() =>
                    navigate(
                      `/login?redirect=${encodeURIComponent(`/course/${course.id}`)}`,
                    )
                  }
                >
                  Войти
                </button>
              )}
              {canUpdateCourse && (
                <>
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={openCourseEditor}
                  >
                    Редактировать курс
                  </button>
                  <button
                    type="button"
                    className="btn btn-solid"
                    onClick={openCourseMetrics}
                  >
                    Посмотреть метрики
                  </button>
                </>
              )}
            </div>
          )}
        </article>
      </section>
    );
  }

  if (!isMetricsMode && !isEnrolled && !canViewWithoutEnrollment) {
    return (
      <section className="container section course-viewer course-enrollment-view">
        <SectionTop label="Курс" title={course?.title || "Просмотр курса"} />
        {error && (
          <article className="glass-card course-viewer-error" role="alert">
            {error}
          </article>
        )}
        <CourseBasicInfo course={course} />
        <article className="glass-card locked-course-card generated-course-enroll-card">
          <div>
            <h2>Содержимое курса закрыто</h2>
            <p>
              Запишитесь на курс, чтобы открыть модули, уроки, теорию, практику
              и ИИ-ментора.
            </p>
          </div>
          <div className="generated-course-actions generated-course-edit-actions">
            <button
              type="button"
              className="btn btn-solid"
              onClick={enrollToCourse}
              disabled={isCourseSigning}
            >
              {isCourseSigning ? "Записываем..." : "Записаться на курс"}
            </button>
            {canUpdateCourse && (
              <>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={openCourseEditor}
                >
                  Редактировать курс
                </button>
                <button
                  type="button"
                  className="btn btn-solid"
                  onClick={openCourseMetrics}
                >
                  Посмотреть метрики
                </button>
              </>
            )}
          </div>
          {enrollmentError && (
            <p className="lesson-ai-error" role="alert">
              {enrollmentError}
            </p>
          )}
        </article>
      </section>
    );
  }

  if (!isMetricsMode && !isLearningStarted) {
    return (
      <section className="container section course-viewer course-enrollment-view">
        <SectionTop label="Курс" title={course?.title || "Просмотр курса"} />
        {error && (
          <article className="glass-card course-viewer-error" role="alert">
            {error}
          </article>
        )}
        <CourseBasicInfo course={course} />
        <article className="glass-card generated-course-enroll-card">
          <div>
            <h2>
              {canViewWithoutEnrollment
                ? "Курс доступен для просмотра"
                : "Курс доступен для прохождения"}
            </h2>
            <p>
              {canViewWithoutEnrollment
                ? "Нажмите кнопку, чтобы открыть структуру курса для чтения."
                : "Нажмите кнопку, чтобы открыть структуру курса и начать обучение."}
            </p>
          </div>
          <div className="generated-course-actions">
            <button
              type="button"
              className="btn btn-solid"
              onClick={startLearning}
            >
              {canViewWithoutEnrollment
                ? "Посмотреть теорию"
                : "Перейти к обучению"}
            </button>
            {canUpdateCourse && (
              <>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={openCourseEditor}
                >
                  Редактировать курс
                </button>
                <button
                  type="button"
                  className="btn btn-solid"
                  onClick={openCourseMetrics}
                >
                  Посмотреть метрики
                </button>
              </>
            )}
          </div>
        </article>
      </section>
    );
  }

  const sectionLabel = isMetricsMode
    ? "Метрики курса"
    : selectedLesson
      ? "Урок"
      : selectedBlock
        ? "Модуль"
        : "Курс";
  const sectionTitle = isMetricsMode
    ? selectedLesson?.title || selectedBlock?.title || course.title
    : selectedLesson?.title || selectedBlock?.title || course.title;
  const isLessonChatEnabled =
    !isMetricsMode && canReadCourseContent && Boolean(selectedLesson);
  const isChatAvailable = isLessonChatEnabled && activeTab === "theory";

  return (
    <section className="container section lesson-view generated-course-learning-view">
      <SectionTop label={sectionLabel} title={sectionTitle} />
      {error && (
        <article className="glass-card course-viewer-error" role="alert">
          {error}
        </article>
      )}
      <LessonChatWorkspace
        className="generated-course-learning-grid"
        chatEnabled={isLessonChatEnabled}
        chatAvailable={isChatAvailable}
        chatKey={selectedLesson?.id || "no-lesson"}
        chatProps={{
          courseId: course.id,
          lessonId: selectedLesson?.id,
          lessonTitle: selectedLesson?.title,
          contentBlocks,
        }}
      >
        {course.blocks.length > 0 ? (
          <CourseNavigationTree
            selectedCourse={course}
            selectedBlock={selectedBlock || course.blocks[0]}
            selectedLessonId={selectedLesson?.id || ""}
            selectedPracticeId=""
            completedLessons={{}}
            completedPractices={{}}
            openBlock={openBlock}
            openLesson={openLesson}
            openPractice={() => {}}
            mode={isMetricsMode ? "metrics" : "theory"}
          />
        ) : (
          <aside className="course-nav-tree generated-course-navigation-shell">
            <p className="course-viewer-muted">В курсе пока нет модулей.</p>
          </aside>
        )}

        <article
          ref={theoryContainerRef}
          className="glass-card lesson-main-card generated-course-main-card"
          onScroll={(event) => {
            event.currentTarget.classList.toggle(
              "is-scrolled",
              event.currentTarget.scrollTop > 8,
            );
          }}
        >
          <div className="lesson-scroll-frame generated-course-scroll-frame">
            {isMetricsMode ? (
              selectedLesson ? (
                <LessonMetricsDashboard
                  courseId={course.id}
                  lesson={selectedLesson}
                />
              ) : (
                <div className="lesson-metrics-dashboard">
                  <div className="metrics-dashboard-head">
                    <div>
                      <span className="metrics-mode-badge">Режим метрик</span>
                      <h2>Выберите урок</h2>
                      <p>
                        Нажмите на урок в дереве курса, чтобы открыть выбор
                        студента и дашборд.
                      </p>
                    </div>
                  </div>
                </div>
              )
            ) : !selectedBlock ? (
              <>
                <CourseBasicInfo course={course} />
                <ModuleList
                  modules={course.blocks}
                  selectedModuleId=""
                  disabled={false}
                  onSelectModule={openBlock}
                />
              </>
            ) : !selectedLesson ? (
              <>
                <ModuleBasicInfo module={moduleBasicInfo} />
                <LessonList
                  lessons={moduleBasicInfo?.lessons || []}
                  selectedLessonId=""
                  onSelectLesson={openLesson}
                />
              </>
            ) : (
              <>
                <div
                  className="lesson-mode-switch"
                  role="tablist"
                  aria-label="Тип материала"
                >
                  <button
                    type="button"
                    className={activeTab === "theory" ? "is-active" : ""}
                    aria-selected={activeTab === "theory"}
                    onClick={() =>
                      setLessonActiveTab(selectedLesson.id, "theory")
                    }
                  >
                    Теория
                  </button>
                  <button
                    type="button"
                    className={activeTab === "questions" ? "is-active" : ""}
                    aria-selected={activeTab === "questions"}
                    onClick={() =>
                      setLessonActiveTab(selectedLesson.id, "questions")
                    }
                  >
                    Проверочные вопросы
                  </button>
                  <button
                    type="button"
                    className={activeTab === "practice" ? "is-active" : ""}
                    aria-selected={activeTab === "practice"}
                    onClick={() =>
                      setLessonActiveTab(selectedLesson.id, "practice")
                    }
                  >
                    Практика
                  </button>
                </div>

                {activeTab === "questions" ? (
                  <LessonTestAgent
                    key={`${selectedBlock.id}:${selectedLesson.id}:test`}
                    moduleId={selectedBlock.id}
                    lessonId={selectedLesson.id}
                  />
                ) : activeTab === "practice" ? (
                  <LessonPracticeAgent
                    key={`${selectedBlock.id}:${selectedLesson.id}:practice`}
                    moduleId={selectedBlock.id}
                    lessonId={selectedLesson.id}
                  />
                ) : (
                  <div className="lesson-theory-content">
                    <p className="course-category">{course.title}</p>
                    <LessonBasicInfo lesson={lessonBasicInfo} />
                    {isLoadingLesson ? (
                      <p className="course-viewer-muted">
                        Загружаем теорию урока...
                      </p>
                    ) : (
                      <ContentBlocks
                        ref={theoryContentRef}
                        blocks={contentBlocks}
                        ownerUserId={courseCreatorId || currentUserId}
                      />
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </article>
      </LessonChatWorkspace>
    </section>
  );
}
