import { DRAG_MIME, MATERIAL_STATUS } from "./constants";
import Icon from "./icons";
import { useDndCourseStore } from "./store";
import { StatusPill, useDndActions } from "./ui";

const ADD_ITEMS = [
  { id: "material", icon: "upload", label: "Загрузить материалы", hint: "PDF, DOCX, TXT и другие документы до 30 МБ" },
  { id: "lesson", icon: "lesson", label: "Создать урок", hint: "Из выделенных или выбранных материалов" },
  { id: "module", icon: "module", label: "Создать модуль", hint: "Из готовых уроков" },
];

export default function Palette({ variant = "side" }) {
  const restartOnboarding = useDndCourseStore((state) => state.restartOnboarding);
  const setPaletteOpen = useDndCourseStore((state) => state.setPaletteOpen);
  const openMaterialPicker = useDndCourseStore((state) => state.openMaterialPicker);
  const openModuleDialog = useDndCourseStore((state) => state.openModuleDialog);
  const createLesson = useDndCourseStore((state) => state.createLessonFromMaterials);
  const { pickFiles } = useDndActions();

  const runAdd = (id) => {
    const state = useDndCourseStore.getState();
    if (id === "material") pickFiles();
    if (id === "lesson") {
      const selected = state.selectedIds
        .filter((item) => item.startsWith("material:"))
        .map((item) => item.slice("material:".length));
      if (selected.length) createLesson(selected);
      else openMaterialPicker();
    }
    if (id === "module") openModuleDialog([], { pick: true });
    if (variant === "sheet") setPaletteOpen(false);
  };

  return (
    <nav className={`dnd-palette dnd-palette--${variant}`} aria-label="Палитра элементов">
      <div className="dnd-palette-head">
        <strong>Палитра</strong>
        <button type="button" className="dnd-icon-btn" onClick={() => setPaletteOpen(false)} aria-label="Свернуть палитру" title="Свернуть палитру">
          <Icon name={variant === "sheet" ? "close" : "panel"} />
        </button>
      </div>

      <section className="dnd-palette-section" aria-labelledby="dnd-palette-add">
        <h3 id="dnd-palette-add">Добавить</h3>
        {ADD_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className="dnd-palette-item"
            draggable
            onDragStart={(event) => {
              event.dataTransfer.setData(DRAG_MIME, item.id);
              event.dataTransfer.effectAllowed = "copy";
            }}
            onClick={() => runAdd(item.id)}
            title={`${item.label}. Можно нажать или перетащить на холст`}
          >
            <span className="dnd-palette-icon">
              <Icon name={item.icon} size={18} />
            </span>
            <span>
              <strong>{item.label}</strong>
              <small>{item.hint}</small>
            </span>
            <Icon name="grip" size={16} className="dnd-palette-grip" />
          </button>
        ))}
      </section>

      <details className="dnd-palette-section dnd-help-group">
        <summary className="dnd-help-group-summary">
          <span>Помощь</span>
          <Icon name="chevronDown" size={16} className="dnd-chevron" />
        </summary>
        <details className="dnd-help">
          <summary>
            <span>Как собрать курс</span>
            <Icon name="chevronDown" size={15} className="dnd-chevron" />
          </summary>
          <ol>
            <li>Загрузите документы — каждый станет материалом.</li>
            <li>Перетащите один или несколько материалов в зону «Новый урок».</li>
            <li>Перетащите уроки на модуль или в зону «Новый модуль».</li>
            <li>Проверьте структуру и нажмите «Завершить».</li>
          </ol>
        </details>
        <details className="dnd-help">
          <summary>
            <span>Типы узлов</span>
            <Icon name="chevronDown" size={15} className="dnd-chevron" />
          </summary>
          <ul className="dnd-help-legend">
            <li><Icon name="file" size={15} /> Материал — текст из документа</li>
            <li><Icon name="lesson" size={15} /> Урок — до 10 блоков материалов</li>
            <li><Icon name="module" size={15} /> Модуль — группа уроков</li>
            <li><Icon name="course" size={15} /> Курс — корень, к нему подключены модули</li>
          </ul>
        </details>
        <details className="dnd-help">
          <summary>
            <span>Статусы</span>
            <Icon name="chevronDown" size={15} className="dnd-chevron" />
          </summary>
          <ul className="dnd-help-legend">
            {Object.entries(MATERIAL_STATUS).map(([key, value]) => (
              <li key={key}>
                <StatusPill tone={value.tone} icon={key === "error" ? "alert" : key === "used" ? "link" : key === "ready" ? "check" : "clock"}>
                  {value.label}
                </StatusPill>
              </li>
            ))}
          </ul>
        </details>
        <details className="dnd-help">
          <summary>
            <span>Подсказки по перетаскиванию</span>
            <Icon name="chevronDown" size={15} className="dnd-chevron" />
          </summary>
          <ul>
            <li>Shift + клик — выделить несколько элементов, Shift + протянуть по холсту — выделить рамкой.</li>
            <li>Пустая область холста двигает рабочее поле, колёсико прокручивает, Ctrl + колёсико — масштаб.</li>
            <li>Можно тянуть линию от точки справа на карточке к другой карточке.</li>
            <li>Всё, что делается перетаскиванием, есть и в кнопках карточек и инспектора.</li>
          </ul>
        </details>
        <button type="button" className="dnd-btn dnd-btn--ghost dnd-btn--sm" onClick={restartOnboarding}>
          <Icon name="restart" size={15} /> Показать обучение снова
        </button>
      </details>
    </nav>
  );
}
