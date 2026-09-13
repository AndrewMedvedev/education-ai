// Витрина готовых курсов, созданных пользователями AI Course Lab
import SectionTop from "../components/SectionTop";

export default function CoursesPage({
  coursesData,
  openCourse,
  openCreator,
  canCreateCourse,
  canReadCourse,
  isLoading = false,
  error = "",
  page = 1,
  pageSize = 9,
  totalPages = 1,
  totalItems = 0,
  onPageChange,
}) {
  const catalogCourses = coursesData;

  const pages = Array.from(
    { length: Math.max(1, totalPages) },
    (_, index) => index + 1,
  );
  const startItem = totalItems > 0 ? (page - 1) * pageSize + 1 : 0;
  const endItem = Math.min(page * pageSize, totalItems);

  return (
    <section className="container section courses-tab" id="courses-tab">
      <SectionTop
        label="Готовые курсы"
        title="Рейтинг курсов, созданных в AI Course Lab"
      />
      <p className="courses-catalog-intro">
        Выбирайте готовые программы по разным темам, смотрите оценки сообщества
        и начинайте обучение сразу. Каждый курс собран с помощью AI Course Lab и
        включает теорию, практику и последовательный учебный маршрут.
      </p>
      {!canReadCourse && (
        <aside className="courses-catalog-cta glass-card">
          <div>
            <span>Доступ ограничен</span>
            <h2>Каталог недоступен для вашей роли</h2>
            <p>
              Обратитесь к администратору организации, чтобы получить доступ к
              просмотру курсов.
            </p>
          </div>
        </aside>
      )}

      {canReadCourse && isLoading && (
        <article className="glass-card courses-catalog-cta">
          <p>Загружаем курсы...</p>
        </article>
      )}

      {canReadCourse && error && (
        <article className="glass-card courses-catalog-cta">
          <p>{error}</p>
        </article>
      )}

      {canReadCourse && !isLoading && !error && catalogCourses.length === 0 && (
        <article className="glass-card courses-catalog-cta">
          <p>Курсы пока не найдены.</p>
        </article>
      )}

      {canReadCourse && !isLoading && !error && catalogCourses.length > 0 && (
        <>
          <div className="courses-catalog-grid">
            {catalogCourses.map((course) => (
              <article
                key={course.id}
                className="course-tab-card glass-card is-clickable"
                role="button"
                tabIndex={0}
                onClick={() => openCourse(course.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openCourse(course.id);
                  }
                }}
              >
                <h3>{course.title}</h3>
                <p>{course.description}</p>
                {Array.isArray(course.tags) && course.tags.length > 0 && (
                  <div className="course-meta-inline" aria-label="Теги курса">
                    {course.tags.map((tag) => (
                      <span key={tag}>{tag}</span>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
          {totalPages > 1 && (
            <nav className="courses-pagination" aria-label="Пагинация курсов">
              <span>
                Показаны {startItem}–{endItem} из {totalItems}
              </span>
              <div className="courses-pagination-actions">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => onPageChange?.(page - 1)}
                  disabled={page <= 1}
                >
                  Назад
                </button>
                {pages.map((pageNumber) => (
                  <button
                    key={pageNumber}
                    type="button"
                    className={`courses-pagination-page ${pageNumber === page ? "is-active" : ""}`}
                    onClick={() => onPageChange?.(pageNumber)}
                    aria-current={pageNumber === page ? "page" : undefined}
                  >
                    {pageNumber}
                  </button>
                ))}
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => onPageChange?.(page + 1)}
                  disabled={page >= totalPages}
                >
                  Вперёд
                </button>
              </div>
            </nav>
          )}
        </>
      )}
      {canCreateCourse && (
        <aside className="courses-catalog-cta glass-card">
          <div>
            <span>Не нашли курс под свою цель?</span>
            <h2>Создайте персональную программу обучения за несколько минут</h2>
            <p>
              Расскажите ИИ, какой навык хотите освоить, — он подготовит
              структуру, уроки и практические задания под ваш уровень.
            </p>
          </div>
          <button type="button" className="btn btn-solid" onClick={openCreator}>
            Создать свой курс
          </button>
        </aside>
      )}
    </section>
  );
}
