// Главная страница с описанием продукта, каталогом треков и механикой генерации
import SectionTop from "../components/SectionTop";

export default function HomePage({
  tracks,
  points,
  steps,
  openCreator,
  openCourses,
  canCreateCourse = false,
  canReadCourse = false,
}) {
  return (
    <>
      <section className="container hero">
        <div className="hero-grid">
          <div className="hero-left glass-card">
            <p className="kicker">ВАША ЦЕЛЬ — ВАШ ПЕРСОНАЛЬНЫЙ КУРС</p>
            <h1>Освойте нужный навык быстрее с курсом, созданным ИИ для вас</h1>
            <p className="lead">
              Опишите, чему хотите научиться, — AI Course Lab за несколько минут
              соберёт понятную программу с теорией, практикой, ИИ-помощником и
              контролем прогресса.
            </p>
            <div className="hero-actions">
              {canCreateCourse && (
                <button
                  type="button"
                  className="btn btn-solid"
                  onClick={openCreator}
                >
                  Сгенерировать курс
                </button>
              )}
              {canReadCourse && (
                <button
                  type="button"
                  className="btn btn-flat"
                  onClick={openCourses}
                >
                  Каталог ИИ-курсов
                </button>
              )}
            </div>
          </div>

          <div className="hero-right glass-card">
            <p className="panel-title">Пример сгенерированного курса</p>
            <div className="line-item">
              <span>01</span>
              <p>Основы ИИ и работа с современными моделями</p>
            </div>
            <div className="line-item">
              <span>02</span>
              <p>Промптинг, контроль качества и верификация ответов</p>
            </div>
            <div className="line-item">
              <span>03</span>
              <p>Практика: автоматизация задач и мини-проекты</p>
            </div>
            <div className="line-item active">
              <span>04</span>
              <p>Итог: персональный AI-workflow для вашей сферы</p>
            </div>
          </div>
        </div>
      </section>

      <section className="container section home-usp">
        <div className="home-usp-copy">
          <p className="kicker">НЕ ИЩИТЕ ПОДХОДЯЩИЙ КУРС — СОЗДАЙТЕ СВОЙ</p>
          <h2>От учебной цели до готового маршрута за несколько минут</h2>
          <p>
            Обычные курсы рассчитаны на всех сразу. AI Course Lab учитывает ваш
            уровень, задачу и доступное время, а затем перестраивает обучение по
            мере вашего прогресса.
          </p>
        </div>
        <div className="home-usp-grid">
          <article className="glass-card">
            <strong>5 минут</strong>
            <span>на создание персональной программы</span>
          </article>
          <article className="glass-card">
            <strong>1 маршрут</strong>
            <span>без лишних тем и случайных материалов</span>
          </article>
          <article className="glass-card">
            <strong>24/7</strong>
            <span>ИИ-помощник объясняет и помогает практиковаться</span>
          </article>
        </div>
      </section>

      <section className="container section" id="about">
        <SectionTop label="01" title="Что вы получаете в AI Course Lab" />
        <div className="point-list">
          {points.map((item) => (
            <article key={item} className="glass-card">
              <p>{item}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="container section" id="tracks">
        <SectionTop label="02" title="Каталог ИИ-курсов" />
        <div className="track-grid">
          {tracks.map((track) => (
            <article key={track.title} className="track-card glass-card">
              <h3>{track.title}</h3>
              <p className="track-desc">{track.description}</p>
              <div className="track-meta">
                <span>{track.modules}</span>
                <span>{track.format}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="container section" id="flow">
        <SectionTop label="03" title="Как генерируется ваш ИИ-курс" />
        <div className="flow-grid">
          {steps.map((step, index) => (
            <article key={step.title} className="glass-card">
              <b>{String(index + 1).padStart(2, "0")}</b>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      {canCreateCourse && (
        <section className="container cta glass-card" id="cta">
          <div>
            <h2>Запустите свой ИИ-курс сегодня</h2>
            <p>
              Одна заявка и вы получаете структуру обучения под вашу задачу.
            </p>
          </div>
          <button type="button" className="btn btn-solid" onClick={openCreator}>
            Старт генерации
          </button>
        </section>
      )}
    </>
  );
}
