import { useEffect, useState } from "react";
import { prefersReducedMotion } from "./helpers";
import Icon from "./icons";
import { getProgress } from "./selectors";
import { useDndCourseStore } from "./store";
import { useDndActions } from "./ui";

export function Onboarding() {
  const dismissed = useDndCourseStore((state) => state.onboardingDismissed);
  const hasMaterials = useDndCourseStore((state) => state.materials.length > 0);
  const dismiss = useDndCourseStore((state) => state.dismissOnboarding);
  const { pickFiles } = useDndActions();
  if (dismissed) return null;
  return (
    <aside className="dnd-onboarding" aria-label="Подсказка по началу работы">
      <div className="dnd-onboarding-icon">
        <Icon name="upload" size={20} />
      </div>
      <div>
        <strong>{hasMaterials ? "Соберите первый урок" : "Перетащите документы на холст, чтобы начать собирать курс."}</strong>
        <ul>
          <li>Материалы → перетащите в зону «Новый урок» внизу холста.</li>
          <li>Уроки → перетащите на модуль, в «Новый модуль» или на другой урок — получится новый модуль.</li>
          <li>Клик по карточке открывает инспектор справа.</li>
        </ul>
        <div className="dnd-onboarding-actions">
          {!hasMaterials ? (
            <button type="button" className="dnd-btn dnd-btn--solid dnd-btn--sm" onClick={() => pickFiles()}>
              <Icon name="upload" size={15} /> Выбрать файлы
            </button>
          ) : null}
          <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={dismiss}>
            Понятно
          </button>
        </div>
      </div>
    </aside>
  );
}

/** Лёгкий праздничный эффект один раз за курс, когда прогресс дошёл до 100%. */
export function Celebration() {
  const percent = useDndCourseStore((state) => getProgress(state).percent);
  const celebrated = useDndCourseStore((state) => state.celebrated);
  const markCelebrated = useDndCourseStore((state) => state.markCelebrated);
  const toast = useDndCourseStore((state) => state.toast);
  const [burst, setBurst] = useState(false);

  useEffect(() => {
    if (percent < 100 || celebrated) return undefined;
    markCelebrated();
    toast("success", "Структура курса собрана — можно проверить и завершить.");
    if (prefersReducedMotion()) return undefined;
    setBurst(true);
    const timer = window.setTimeout(() => setBurst(false), 1600);
    return () => window.clearTimeout(timer);
  }, [percent, celebrated, markCelebrated, toast]);

  if (!burst) return null;
  return (
    <div className="dnd-confetti" aria-hidden="true">
      {Array.from({ length: 18 }, (_, index) => (
        <i key={index} style={{ "--i": index }} />
      ))}
    </div>
  );
}
