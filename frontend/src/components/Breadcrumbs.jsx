import { Link, useLocation } from "react-router-dom";
import { useUiLayoutStore } from "../stores/uiLayoutStore";

const staticRoutes = {
  courses: "Каталог",
  creator: "Создание курса",
  "manual-course-builder": "Создать курс самостоятельно",
  profile: "Личный кабинет",
  login: "Вход",
  register: "Регистрация",
};

export default function Breadcrumbs({
  selectedCourse,
  selectedBlock,
  selectedLesson,
  selectedPractice,
}) {
  const location = useLocation();
  const routeHistory = useUiLayoutStore((state) => state.routeHistory);
  const segments = location.pathname.split("/").filter(Boolean);
  const currentRoute = `${location.pathname}${location.search || ""}${location.hash || ""}`;
  const previousRoute = [...routeHistory]
    .reverse()
    .find(
      (route) =>
        route !== currentRoute && route !== "/login" && route !== "/register",
    );

  if (segments.length === 0) {
    return null;
  }

  const crumbs = [{ label: "Главная", to: "/" }];

  if (segments[0] !== "course") {
    crumbs.push({
      label: staticRoutes[segments[0]] || "Раздел",
      to: location.pathname,
    });
  } else {
    const courseId = selectedCourse?.id || segments[1];
    const mode =
      segments[2] === "edit" || segments[2] === "metrics" ? segments[2] : "";
    const contentTypeIndex = mode ? 3 : 2;
    const contentType = segments[contentTypeIndex];
    const courseRoute = courseId ? `/course/${courseId}` : location.pathname;
    const modeRoute = mode && courseId ? `${courseRoute}/${mode}` : "";

    crumbs.push({ label: "Каталог", to: "/courses" });
    crumbs.push({
      label: selectedCourse?.title || "Курс",
      to: mode === "edit" ? modeRoute : courseRoute,
    });

    if (mode === "metrics") {
      crumbs.push({ label: "Метрики", to: modeRoute });
    }

    if (contentType === "block" && selectedBlock) {
      crumbs.push({ label: selectedBlock.title, to: location.pathname });
    }

    if (
      (contentType === "lesson" || contentType === "lessons") &&
      selectedLesson
    ) {
      crumbs.push({ label: selectedLesson.title, to: location.pathname });
    }

    if (contentType === "practice" && selectedPractice) {
      crumbs.push({ label: selectedPractice.title, to: location.pathname });
    }
  }

  return (
    <nav className="container breadcrumbs" aria-label="Хлебные крошки">
      <ol>
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          return (
            <li key={`${crumb.to}-${crumb.label}`}>
              {isLast ? (
                <span aria-current="page">{crumb.label}</span>
              ) : (
                <Link to={crumb.to} replace={crumb.to === previousRoute}>
                  {crumb.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
