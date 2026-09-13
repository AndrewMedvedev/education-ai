export default function EnrollmentStatus({ isEnrolled, isSubmitting, onEnroll }) {
  return (
    <article className="course-viewer-card enrollment-status">
      <div>
        <div className="course-viewer-eyebrow">Статус записи</div>
        <h2>{isEnrolled ? "Вы записаны на курс" : "Вы пока не записаны"}</h2>
        <p className="course-viewer-muted">
          {isEnrolled
            ? "Модули и уроки доступны для изучения."
            : "Запишитесь, чтобы открыть модули, уроки и теорию курса."}
        </p>
      </div>
      {!isEnrolled && (
        <button
          type="button"
          className="btn btn-solid course-enroll-button"
          onClick={onEnroll}
          disabled={isSubmitting}
        >
          {isSubmitting ? "Записываем..." : "Записаться на курс"}
        </button>
      )}
    </article>
  );
}
