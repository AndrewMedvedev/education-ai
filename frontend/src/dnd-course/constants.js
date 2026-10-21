export const DRAFT_KEY = "drag_and_drop_course_draft_v2";
export const LEGACY_DRAFT_KEY = "manual_course_builder_draft_v1";

export const MAX_FILE_SIZE_BYTES = 30 * 1024 * 1024;
export const MAX_FILE_SIZE_LABEL = "30 МБ";

export const INTERRUPTED_UPLOAD_MESSAGE =
  "Загрузка была прервана. Добавьте файл повторно или удалите материал.";

export const DIFFICULTY_OPTIONS = [
  { value: "beginner", label: "Начальный" },
  { value: "intermediate", label: "Средний" },
  { value: "advanced", label: "Продвинутый" },
  { value: "expert", label: "Экспертный" },
];

export const DIFFICULTY_LABEL = Object.fromEntries(
  DIFFICULTY_OPTIONS.map((option) => [option.value, option.label]),
);

export const EMPTY_COURSE_FORM = {
  title: "",
  description: "",
  difficulty: "beginner",
  tags: "",
};

// Размеры узлов на холсте. Модуль растягивается по числу уроков внутри.
// Узлы крупные: курсы собирают в основном взрослые пользователи, текст должен легко читаться.
export const NODE_SIZE = {
  course: { width: 400, height: 330 },
  material: { width: 350, height: 178 },
  lesson: { width: 372, height: 162 },
  upload: { width: 350, height: 134 },
};

export const MODULE_LAYOUT = {
  width: 420,
  header: 172,
  lessonGap: 14,
  padding: 24,
  footer: 82,
};

export const COLUMN_X = {
  material: 0,
  lesson: 460,
  module: 950,
  course: 1500,
};

export const COLUMN_GAP = 18;

export const MATERIAL_STATUS = {
  uploading: { label: "Обрабатываем документ", short: "Обработка", tone: "progress" },
  ready: { label: "Материал готов", short: "Готов", tone: "ok" },
  error: { label: "Не удалось обработать", short: "Ошибка", tone: "error" },
  used: { label: "Добавлен в урок", short: "В уроке", tone: "used" },
};

export const FILTERS = [
  { id: "all", label: "Все материалы" },
  { id: "ready", label: "Готовые материалы" },
  { id: "errors", label: "Материалы с ошибками" },
  { id: "unassigned", label: "Уроки без модуля" },
  { id: "modules", label: "Модули" },
  { id: "incomplete", label: "Незавершённые элементы" },
];

export const DRAG_MIME = "application/x-dnd-course";
