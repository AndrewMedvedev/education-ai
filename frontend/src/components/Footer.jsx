// Полноценный футер с навигацией по продукту и служебными ссылками
import { Link } from "react-router-dom";

export default function Footer({
  canCreateCourse = false,
  canReadCourse = false,
}) {
  return (
    <footer className="footer-shell">
      <div className="container footer">
        <div className="footer-brand">
          <Link to="/" className="logo">
            <span className="logo-main">AI Course Lab</span>
            <span className="logo-sub">обучение, созданное под вас</span>
          </Link>
          <p>
            Персональные курсы с теорией, практикой и ИИ-помощником под вашу
            цель и уровень.
          </p>
        </div>
        <div className="footer-column">
          <strong>Продукт</strong>
          {canReadCourse && <Link to="/courses">Каталог курсов</Link>}
          {canCreateCourse && <Link to="/creator">Создать курс</Link>}
        </div>
        <div className="footer-column">
          <strong>Аккаунт</strong>
          <Link to="/profile">Личный кабинет</Link>
          <Link to="/login">Войти</Link>
          <Link to="/register">Регистрация</Link>
        </div>
        <div className="footer-column">
          <strong>Поддержка</strong>
          <a href="mailto:support@aicourselab.ru">Связаться с нами</a>
          <a href="#privacy">Политика конфиденциальности</a>
          <a href="#terms">Условия использования</a>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© 2026 AI Course Lab</span>
        <span>Курсы нового поколения</span>
      </div>
    </footer>
  );
}
