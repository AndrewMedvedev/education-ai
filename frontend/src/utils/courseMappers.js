const sortByOrder = (items) =>
  [...(Array.isArray(items) ? items : [])].sort((first, second) => {
    const firstOrder = Number.isFinite(first?.order)
      ? first.order
      : Number.MAX_SAFE_INTEGER;
    const secondOrder = Number.isFinite(second?.order)
      ? second.order
      : Number.MAX_SAFE_INTEGER;
    return firstOrder - secondOrder;
  });

const normalizeText = (value, fallback = "") =>
  typeof value === "string" ? value : fallback;

const normalizeArray = (value) => (Array.isArray(value) ? value : []);

export function toBasicInfo(entity) {
  if (!entity || typeof entity !== "object") {
    return null;
  }

  return {
    id: entity.id ?? "",
    title: normalizeText(entity.title, "Без названия"),
    order: Number.isFinite(entity.order) ? entity.order : 0,
  };
}

export function toCourseBasicInfo(course) {
  if (!course || typeof course !== "object") {
    return null;
  }

  return {
    id: course.id ?? "",
    title: normalizeText(course.title, "Курс без названия"),
    description: normalizeText(course.description),
    difficulty: normalizeText(course.difficulty, "Не указан"),
    tags: normalizeArray(course.tags).filter((tag) => typeof tag === "string"),
    learning_objectives: normalizeArray(course.learning_objectives).filter(
      (objective) => typeof objective === "string",
    ),
    modules: sortByOrder(course.modules).map(toBasicInfo).filter(Boolean),
  };
}

export function toModuleBasicInfo(module) {
  if (!module || typeof module !== "object") {
    return null;
  }

  return {
    id: module.id ?? "",
    title: normalizeText(module.title, "Модуль без названия"),
    description: normalizeText(module.description),
    order: Number.isFinite(module.order) ? module.order : 0,
    learning_objectives: normalizeArray(module.learning_objectives).filter(
      (objective) => typeof objective === "string",
    ),
    lessons: sortByOrder(module.lessons).map(toBasicInfo).filter(Boolean),
  };
}

export function toLessonBasicInfo(lesson) {
  if (!lesson || typeof lesson !== "object") {
    return null;
  }

  return {
    id: lesson.id ?? "",
    title: normalizeText(lesson.title, "Урок без названия"),
    description: normalizeText(lesson.description),
    order: Number.isFinite(lesson.order) ? lesson.order : 0,
    learning_objectives: normalizeArray(lesson.learning_objectives).filter(
      (objective) => typeof objective === "string",
    ),
    estimated_time_minutes: Number.isFinite(lesson.estimated_time_minutes)
      ? lesson.estimated_time_minutes
      : null,
  };
}

export function getSortedModules(course) {
  return sortByOrder(course?.modules);
}

export function getSortedLessons(module) {
  return sortByOrder(module?.lessons);
}

export function normalizeContentBlocks(blocks) {
  return normalizeArray(blocks).filter(
    (block) => block && typeof block === "object",
  );
}

function contentBlockToMarkdown(block, index) {
  if (!block || typeof block !== "object") {
    return "";
  }

  const title =
    typeof block.title === "string" && block.title.trim()
      ? `### ${block.title.trim()}`
      : `### Блок ${index + 1}`;

  if (block.content_type === "text") {
    const text = [
      block.md_content,
      block.content,
      block.text,
      block.explanation,
    ].find((value) => typeof value === "string" && value.trim());
    return [title, text || "Текстовый блок пуст."].join("\n\n");
  }

  if (block.content_type === "program_code") {
    const language =
      typeof block.language === "string" && block.language.trim()
        ? block.language.trim()
        : "text";
    const code = typeof block.code === "string" ? block.code : "";
    const explanation =
      typeof block.explanation === "string" ? block.explanation : "";
    return [title, `\`\`\`${language}\n${code}\n\`\`\``, explanation]
      .filter(Boolean)
      .join("\n\n");
  }

  if (block.content_type === "video") {
    return [
      title,
      block.url ? `[Видео](${block.url})` : "Видео без ссылки.",
      block.description,
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  if (block.content_type === "image") {
    return [
      title,
      block.image_url ? `![](${block.image_url})` : "Изображение не указано.",
    ].join("\n\n");
  }

  if (block.content_type === "mermaid") {
    return [
      typeof block.title === "string" && block.title.trim()
        ? `### ${block.title.trim()}`
        : title,
      `\`\`\`mermaid\n${block.md_content || ""}\n\`\`\``,
      block.explanation,
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  if (block.content_type === "quiz") {
    const questions = Array.isArray(block.questions) ? block.questions : [];
    const markdownQuestions = questions.map((question, questionIndex) => {
      const parts = Array.isArray(question) ? question : [question];
      const questionTitle =
        typeof question?.question === "string"
          ? question.question
          : typeof parts[0] === "string"
            ? parts[0]
            : `Вопрос ${questionIndex + 1}`;
      const answer =
        typeof question?.answer === "string"
          ? question.answer
          : parts
              .slice(1)
              .filter((part) => typeof part === "string")
              .join("\n");
      return [`${questionIndex + 1}. **${questionTitle}**`, answer]
        .filter(Boolean)
        .join("\n\n");
    });

    return [title, "#### Проверочные вопросы", ...markdownQuestions].join(
      "\n\n",
    );
  }

  if (
    ["math_formula", "chemical_formula", "musical_notation"].includes(
      block.content_type,
    )
  ) {
    return [title, block.formula, block.explanation]
      .filter(Boolean)
      .join("\n\n");
  }

  return [
    title,
    `Неподдерживаемый тип блока: ${block.content_type || "unknown"}`,
  ].join("\n\n");
}

function contentBlocksToMarkdown(blocks) {
  return normalizeContentBlocks(blocks)
    .map(contentBlockToMarkdown)
    .filter(Boolean)
    .join("\n\n---\n\n");
}

export function toLearningCourse(course) {
  const courseBasicInfo = toCourseBasicInfo(course);

  if (!courseBasicInfo) {
    return null;
  }

  return {
    ...courseBasicInfo,
    category: courseBasicInfo.difficulty,
    learningObjectives: courseBasicInfo.learning_objectives,
    duration: "По индивидуальному темпу",
    level: courseBasicInfo.difficulty,
    format: "Теория + практика",
    blocks: getSortedModules(course).map((module) => ({
      id: module.id ?? "",
      title: normalizeText(module.title, "Модуль без названия"),
      description: normalizeText(module.description),
      order: Number.isFinite(module.order) ? module.order : 0,
      duration: "Модуль курса",
      learningObjectives: normalizeArray(module.learning_objectives).filter(
        (objective) => typeof objective === "string",
      ),
      lessons: getSortedLessons(module).map((lesson) => {
        const markdown = contentBlocksToMarkdown(lesson.content_blocks);

        return {
          id: lesson.id ?? "",
          title: normalizeText(lesson.title, "Урок без названия"),
          duration: Number.isFinite(lesson.estimated_time_minutes)
            ? `${lesson.estimated_time_minutes} мин.`
            : "Время не указано",
          summary: normalizeText(lesson.description),
          content: markdown || normalizeText(lesson.description),
          markdown,
          contentBlocks: normalizeContentBlocks(lesson.content_blocks),
          order: Number.isFinite(lesson.order) ? lesson.order : 0,
        };
      }),
      practice: [],
    })),
  };
}
