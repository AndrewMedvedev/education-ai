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
  isUserEnrolled,
} from "../../services/courseService";
import ContentBlocks from "./ContentBlocks";
import CourseInviteDialog from "./CourseInviteDialog";
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
import { useCourseProgress } from "../../hooks/useCourseProgress";
import { getModuleProgressSummary } from "../../services/progressService";
import { getErrorMessage } from "../../utils/errors";
import { isTokenExpired, isUuid } from "../../utils/api";
import ModuleList from "./ModuleList";
import LessonMetricsDashboard from "./LessonMetricsDashboard";
import "./course-viewer.css";

function findBlockByLesson(course, lessonId) {
  if (!lessonId) return null;
  return (
    course?.blocks?.find((block) =>
      (block.lessons || []).some((lesson) => lesson.id === lessonId),
    ) ?? null
  );
}

// Краткая информация о курсе приходит без уроков: подставляем уроки из полной
// структуры, чтобы дерево могло показать прогресс по каждому уроку.
function mergeCourseLessons(course, structure) {
  if (!course || !structure?.blocks?.length) {
    return course;
  }

  let isChanged = false;
  const blocks = course.blocks.map((block) => {
    const fullBlock = structure.blocks.find((item) => item.id === block.id);
    if (!fullBlock?.lessons?.length || block.lessons?.length) {
      return block;
    }
    isChanged = true;
    return { ...block, lessons: fullBlock.lessons };
  });

  return isChanged ? { ...course, blocks } : course;
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

function CourseProgressBar({ summary }) {
  return (
    <div className="course-progress-summary">
      <div className="course-progress-summary-row">
        <span>
          Пройдено уроков: {summary.completed} из {summary.total}
        </span>
        <b>{summary.percent}%</b>
      </div>
      <div
        className="course-nav-progress-bar"
        role="progressbar"
        aria-label="Прогресс курса"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={summary.percent}
      >
        <span style={{ width: `${summary.percent}%` }} />
      </div>
    </div>
  );
}

const ASSESSMENT_PASSING_SCORE = 61;

function isAssessmentPassed(result) {
  const score = Number(result?.score);
  if (Number.isFinite(score)) return score >= ASSESSMENT_PASSING_SCORE;
  const explicit = result?.is_passed ?? result?.isPassed ?? result?.passed;
  return explicit === true;
}

function LessonPartMark({ done }) {
  return (
    <span
      className={`lesson-mode-progress ${done ? "is-done" : ""}`}
      title={done ? "Пройдено" : "Ещё не пройдено"}
      aria-label={done ? "Пройдено" : "Ещё не пройдено"}
    />
  );
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
  const loadedCourseIdRef = useRef(null);
  const [selectedModuleId, setSelectedModuleId] = useState(blockId ?? null);
  const [selectedLessonId, setSelectedLessonId] = useState(lessonId ?? null);
  const [isLearningStarted, setIsLearningStarted] = useState(
    Boolean(blockId || lessonId),
  );
  const [contentBlocks, setContentBlocks] = useState([]);
  const [contentLessonId, setContentLessonId] = useState(null);
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
  const canInviteToCourse = isOwnCourse || canUpdateCourse;
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const inviteControls = canInviteToCourse ? (
    <>
      <button
        type="button"
        className="btn btn-outline"
        onClick={() => setIsInviteOpen(true)}
      >
        Пригласить
      </button>
      <CourseInviteDialog
        open={isInviteOpen}
        onClose={() => setIsInviteOpen(false)}
        courseId={course?.id || effectiveCourseId}
        courseTitle={course?.title}
        canViewMembers={canUpdateCourse}
        currentUserId={currentUserId}
      />
    </>
  ) : null;
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

  // Прогресс ведём только для записанного ученика, но не при авторском просмотре.
  const isProgressTracked =
    mode === "view" &&
    canReadCourseContent &&
    isEnrolled &&
    !isOwnCourse &&
    isUuid(course?.id || "");
  const shouldTrackTheorySession = isProgressTracked && activeTab === "theory";
  const {
    isLoading: isProgressLoading,
    error: progressError,
    lessonProgressById,
    structure: progressStructure,
    summary: progressSummary,
    trackLesson,
    completeTheory,
    refreshLesson,
  } = useCourseProgress(course?.id, { enabled: isProgressTracked });
  const selectedLessonProgress = selectedLesson
    ? lessonProgressById[selectedLesson.id]
    : null;
  const moduleProgressById = useMemo(() => {
    if (!isProgressTracked || !course) {
      return null;
    }
    return Object.fromEntries(
      course.blocks.map((block) => [
        block.id,
        getModuleProgressSummary(block, lessonProgressById),
      ]),
    );
  }, [course, isProgressTracked, lessonProgressById]);

  useTheorySessionTracker(selectedLesson?.id, {
    enabled: shouldTrackTheorySession,
    scrollContainerRef: theoryContainerRef,
    contentRef: theoryContentRef,
    // При смене адреса курс перезагружается и теория монтируется заново —
    // учитываем это, иначе трекер держит ссылку на уже снятый DOM-узел.
    isContentReady:
      !isLoadingCourse &&
      !isLoadingLesson &&
      !error &&
      Boolean(selectedLesson?.id) &&
      contentLessonId === selectedLesson?.id,
    // Теория засчитывается автоматически, когда ученик долистал её до конца.
    onReachEnd: isProgressTracked
      ? (reachedLessonId) =>
          completeTheory(
            findBlockByLesson(course, reachedLessonId)?.id || selectedBlock?.id,
            reachedLessonId,
          )
      : null,
    canReachEnd:
      !isLoadingLesson &&
      Boolean(selectedLesson?.id) &&
      contentLessonId === selectedLesson?.id,
  });

  useEffect(() => {
    if (progressStructure && course) {
      // mergeCourseLessons возвращает тот же объект, если подставлять нечего.
      setCourse((currentCourse) =>
        mergeCourseLessons(currentCourse, progressStructure),
      );
    }
  }, [course, progressStructure]);

  useEffect(() => {
    if (isProgressTracked && selectedBlock?.id && selectedLesson?.id) {
      trackLesson(selectedBlock.id, selectedLesson.id);
    }
  }, [isProgressTracked, selectedBlock?.id, selectedLesson?.id, trackLesson]);

  const handleAssessmentChecked = (field) => (result) => {
    const targetModuleId = selectedBlock?.id;
    const targetLessonId = selectedLesson?.id;
    if (
      !isProgressTracked ||
      !targetModuleId ||
      !targetLessonId ||
      !isAssessmentPassed(result)
    ) {
      return;
    }

    void trackLesson(targetModuleId, targetLessonId).then((progress) => {
      if (progress) refreshLesson(targetLessonId, field);
    });
  };

  useEffect(() => {
    let isMounted = true;

    async function loadCourse() {
      // При переходе по урокам того же курса не показываем полноэкранную загрузку:
      // иначе дерево и теория пересоздаются, а дерево прыгает в начало.
      const isSameCourse = loadedCourseIdRef.current === effectiveCourseId;
      if (!isSameCourse) {
        setIsLoadingCourse(true);
      }
      setError(null);

      try {
        if (!effectiveCourseId) {
          throw new Error("Идентификатор курса не указан");
        }

        // Прямая ссылка или обновление страницы на модуле/уроке: в краткой информации
        // о курсе уроков нет, поэтому догружаем структуру, иначе урок из адреса
        // не находится и вместо него открывается обзор курса.
        const isDeepLink =
          isUuid(effectiveCourseId) && Boolean(blockId || lessonId);
        let basicCourse =
          isMetricsMode || isDeepLink
            ? await getCourseLearningStructure(effectiveCourseId)
            : !isUuid(effectiveCourseId) &&
                localCourse?.id === effectiveCourseId
              ? localCourse
              : await getCourseBasicInfo(effectiveCourseId);

        if (!isMetricsMode && isDeepLink && lessonId && isUuid(lessonId)) {
          await getLessonById(lessonId).catch(() => null);
          basicCourse = await getCourseBasicInfo(effectiveCourseId);
        }

        const basicCourseCreatorId =
          basicCourse?.creator_id ||
          basicCourse?.creatorId ||
          basicCourse?.author_id ||
          basicCourse?.authorId ||
          basicCourse?.user_id ||
          basicCourse?.userId;
        const isBasicCourseOwn = Boolean(
          currentUserId &&
          basicCourseCreatorId &&
          currentUserId === basicCourseCreatorId,
        );
        let enrollmentPage = null;
        if (!isMetricsMode && canReadCourseContent && !isBasicCourseOwn) {
          enrollmentPage = await loadMyCourses({ page: 1, size: 100 });
        }

        const enrolled =
          canReadCourseContent && !isBasicCourseOwn && enrollmentPage
            ? await isUserEnrolled(basicCourse.id, enrollmentPage)
            : false;

        if (!isMounted) {
          return;
        }

        loadedCourseIdRef.current = effectiveCourseId;
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
    currentUserId,
    localCourse,
  ]);

  useEffect(() => {
    if (
      isMetricsMode ||
      !canReadCourseContent ||
      (!isEnrolled && !canViewWithoutEnrollment) ||
      !selectedLesson?.id
    ) {
      setContentBlocks([]);
      setContentLessonId(null);
      return;
    }

    let isMounted = true;

    async function loadLessonContent() {
      setIsLoadingLesson(true);
      setContentLessonId(null);
      setError(null);

      try {
        const lessonBlocks = await getLessonContentBlocks(selectedLesson.id);

        if (isMounted) {
          setContentBlocks(lessonBlocks);
          setContentLessonId(selectedLesson.id);
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
  }, [
    canReadCourseContent,
    canViewWithoutEnrollment,
    isEnrolled,
    isMetricsMode,
    selectedLesson?.id,
  ]);

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
            {inviteControls}
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
            {isProgressTracked && (
              <>
                <CourseProgressBar summary={progressSummary} />
                {isProgressLoading && (
                  <p className="course-viewer-muted" role="status">
                    Загружаем прогресс...
                  </p>
                )}
                {progressError && (
                  <p className="lesson-ai-error" role="alert">
                    {progressError}
                  </p>
                )}
              </>
            )}
          </div>
          <div className="generated-course-actions">
            <button
              type="button"
              className="btn btn-solid"
              onClick={startLearning}
            >
              {canViewWithoutEnrollment
                ? "Посмотреть теорию"
                : isProgressTracked && progressSummary.started > 0
                  ? "Продолжить обучение"
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
            {inviteControls}
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
      {isProgressTracked && progressError && (
        <article className="glass-card course-viewer-error" role="alert">
          {progressError}
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
            lessonProgressById={isProgressTracked ? lessonProgressById : null}
            progressSummary={progressSummary}
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
                  progressById={moduleProgressById}
                />
              </>
            ) : !selectedLesson ? (
              <>
                <ModuleBasicInfo module={moduleBasicInfo} />
                <LessonList
                  lessons={moduleBasicInfo?.lessons || []}
                  selectedLessonId=""
                  onSelectLesson={openLesson}
                  progressById={isProgressTracked ? lessonProgressById : null}
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
                    {isProgressTracked && (
                      <LessonPartMark
                        done={Boolean(
                          selectedLessonProgress?.theoryCompletedAt,
                        )}
                      />
                    )}
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
                    {isProgressTracked && (
                      <LessonPartMark
                        done={Boolean(selectedLessonProgress?.testCompletedAt)}
                      />
                    )}
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
                    {isProgressTracked && (
                      <LessonPartMark
                        done={Boolean(
                          selectedLessonProgress?.practiceCompletedAt,
                        )}
                      />
                    )}
                  </button>
                </div>

                {activeTab === "questions" ? (
                  <LessonTestAgent
                    key={`${selectedBlock.id}:${selectedLesson.id}:test`}
                    moduleId={selectedBlock.id}
                    lessonId={selectedLesson.id}
                    onChecked={handleAssessmentChecked("testCompletedAt")}
                  />
                ) : activeTab === "practice" ? (
                  <LessonPracticeAgent
                    key={`${selectedBlock.id}:${selectedLesson.id}:practice`}
                    moduleId={selectedBlock.id}
                    lessonId={selectedLesson.id}
                    onChecked={handleAssessmentChecked("practiceCompletedAt")}
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
                        lessonId={selectedLesson.id}
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
