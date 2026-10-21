import { COLUMN_GAP, COLUMN_X, MODULE_LAYOUT, NODE_SIZE } from "./constants";

export function moduleHeight(lessonCount) {
  const lessonsHeight =
    lessonCount > 0
      ? lessonCount * NODE_SIZE.lesson.height +
        (lessonCount - 1) * MODULE_LAYOUT.lessonGap
      : 0;
  return MODULE_LAYOUT.header + lessonsHeight + MODULE_LAYOUT.footer;
}

export function lessonOffsetInModule(index) {
  return {
    x: (MODULE_LAYOUT.width - NODE_SIZE.lesson.width) / 2,
    y:
      MODULE_LAYOUT.header +
      index * (NODE_SIZE.lesson.height + MODULE_LAYOUT.lessonGap),
  };
}

function overlaps(a, b) {
  return (
    a.x < b.x + b.width + COLUMN_GAP &&
    a.x + a.width + COLUMN_GAP > b.x &&
    a.y < b.y + b.height + COLUMN_GAP &&
    a.y + a.height + COLUMN_GAP > b.y
  );
}

/** Ищет ближайшее свободное место под desired, сдвигаясь вниз. */
export function findFreeSlot(desired, size, rects) {
  const candidate = { x: desired.x, y: desired.y, ...size };
  for (let guard = 0; guard < 400; guard += 1) {
    const hit = rects.find((rect) => overlaps(candidate, rect));
    if (!hit) return { x: candidate.x, y: candidate.y };
    candidate.y = hit.y + hit.height + COLUMN_GAP;
  }
  return { x: candidate.x, y: candidate.y };
}

/**
 * Прямоугольники модулей. Модуль, который пользователь перетащил, стоит там, где его
 * оставили (positions["module:<id>"]); остальные идут колонкой по порядку и не ложатся
 * поверх перенесённых.
 */
export function modulesColumn(modules, positions = {}) {
  const ordered = [...modules].sort((a, b) => a.order - b.order);
  const sizeOf = (module) => ({
    width: MODULE_LAYOUT.width,
    height: moduleHeight((module.lessonIds || []).length),
  });
  const savedOf = (module) => {
    const saved = positions?.[`module:${module.id}`];
    return saved && Number.isFinite(saved.x) && Number.isFinite(saved.y) ? saved : null;
  };
  const placed = ordered
    .filter((module) => savedOf(module))
    .map((module) => ({ id: module.id, ...savedOf(module), ...sizeOf(module) }));
  const rects = new Map(placed.map((rect) => [rect.id, rect]));
  let y = 0;
  ordered.forEach((module) => {
    if (rects.has(module.id)) return;
    const size = sizeOf(module);
    const spot = findFreeSlot({ x: COLUMN_X.module, y }, size, [...rects.values()]);
    const rect = { id: module.id, ...spot, ...size };
    rects.set(module.id, rect);
    y = spot.y + size.height + COLUMN_GAP * 2;
  });
  return ordered.map((module) => rects.get(module.id));
}

/**
 * Позиции «свободных» узлов: курс, загрузка, материалы, уроки без модуля.
 * Сохранённые координаты имеют приоритет, остальные раскладываются по колонкам
 * Материалы → Уроки → Модули → Курс без наложений.
 */
export function resolveFreePositions(state) {
  const positions = state.positions || {};
  const resolved = {};
  const rects = [];
  const assigned = new Set(
    (state.modules || []).flatMap((module) => module.lessonIds || []),
  );

  modulesColumn(state.modules || [], positions).forEach((rect) => rects.push(rect));

  const place = (id, size, fallback) => {
    const saved = positions[id];
    const position =
      saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)
        ? saved
        : findFreeSlot(fallback, size, rects);
    resolved[id] = position;
    rects.push({ id, ...position, ...size });
  };

  // Сначала узлы с сохранёнными координатами, чтобы новые не легли поверх них.
  const entries = [
    ["course", NODE_SIZE.course, { x: COLUMN_X.course, y: 0 }],
    ["upload", NODE_SIZE.upload, { x: COLUMN_X.material, y: 0 }],
    ...(state.materials || [])
      .filter((material) => state.showUsedMaterials || !material.lessonId)
      .map((material) => [
      `material:${material.id}`,
      NODE_SIZE.material,
      { x: COLUMN_X.material, y: NODE_SIZE.upload.height + COLUMN_GAP },
    ]),
    ...(state.lessons || [])
      .filter((lesson) => !assigned.has(lesson.id))
      .map((lesson) => [
        `lesson:${lesson.id}`,
        NODE_SIZE.lesson,
        { x: COLUMN_X.lesson, y: 0 },
      ]),
  ];

  entries
    .filter(([id]) => positions[id])
    .forEach(([id, size, fallback]) => place(id, size, fallback));
  entries
    .filter(([id]) => !positions[id])
    .forEach(([id, size, fallback]) => place(id, size, fallback));

  return resolved;
}

export function freeRects(state, excludeIds = []) {
  const resolved = resolveFreePositions(state);
  const sizes = {
    course: NODE_SIZE.course,
    upload: NODE_SIZE.upload,
    material: NODE_SIZE.material,
    lesson: NODE_SIZE.lesson,
  };
  const rects = Object.entries(resolved)
    .filter(([id]) => !excludeIds.includes(id))
    .map(([id, position]) => ({
      id,
      ...position,
      ...(sizes[id.split(":")[0]] || NODE_SIZE.material),
    }));
  return [...rects, ...modulesColumn(state.modules || [], state.positions || {})];
}
