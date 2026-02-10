import {
  renderCodeContent,
  renderMermaidContent,
  renderQuizContent,
  renderTextContent,
  renderVideoContent,
} from "./render.js";

import { getContentTypeLabel } from "./utils.js";

// Глобальная переменная для хранения данных курса
let courseData = null;
let currentModuleIndex = 0;

// Функция инициализации приложения
export function initApp(courseJson) {
  courseData = courseJson;
  currentModuleIndex = 0;

  // Создаем верхнюю навигацию (только индикатор прогресса)
  renderTopNavigation();

  // Рендерим первый модуль
  renderModule(courseData.modules[0]);

  // Создаем нижнюю навигацию (кнопки)
  renderBottomNavigation();
}

// Функция для создания верхней навигации
function renderTopNavigation() {
  const navContainer = document.createElement("div");
  navContainer.className = "top-navigation-container";

  const navHTML = `
    <div class="top-navigation">
      <div class="nav-info">
        <span id="module-counter">Модуль 1 из ${courseData.modules.length}</span>
        <div class="module-progress">
          ${courseData.modules
            .map(
              (_, index) => `
            <div class="progress-dot ${index === 0 ? "active" : ""}" data-module-index="${index}"></div>
          `,
            )
            .join("")}
        </div>
      </div>
    </div>
    <div class="module-list">
      <h3>Содержание курса:</h3>
      ${courseData.modules
        .map(
          (module, index) => `
        <div class="module-item ${index === 0 ? "active" : ""}" data-module-index="${index}">
          <div class="module-item-order">${index + 1}</div>
          <div class="module-item-content">
            <h4>${module.title}</h4>
            <p>${module.description.substring(0, 100)}...</p>
          </div>
        </div>
      `,
        )
        .join("")}
    </div>
  `;

  navContainer.innerHTML = navHTML;

  // Вставляем верхнюю навигацию перед основным контентом
  const app = document.getElementById("app");
  app.before(navContainer);

  // Добавляем обработчики событий для верхней навигации
  setupTopNavigationEvents();
}

// Функция для создания нижней навигации (кнопки)
function renderBottomNavigation() {
  const bottomNavContainer = document.createElement("div");
  bottomNavContainer.className = "bottom-navigation-container";

  const bottomNavHTML = `
    <div class="bottom-navigation">
      <button id="prev-btn" class="nav-btn prev-btn" disabled>
        <span class="nav-btn-icon">←</span>
        <span class="nav-btn-text">Предыдущий модуль</span>
      </button>
      <button id="next-btn" class="nav-btn next-btn">
        <span class="nav-btn-text">Следующий модуль</span>
        <span class="nav-btn-icon">→</span>
      </button>
    </div>
  `;

  bottomNavContainer.innerHTML = bottomNavHTML;

  // Вставляем нижнюю навигацию после основного контента
  const app = document.getElementById("app");
  app.after(bottomNavContainer);

  // Добавляем обработчики событий для нижней навигации
  setupBottomNavigationEvents();
}

// Настройка обработчиков событий для верхней навигации
function setupTopNavigationEvents() {
  // Клики по точкам прогресса
  document.querySelectorAll(".progress-dot").forEach((dot) => {
    dot.addEventListener("click", (e) => {
      const moduleIndex = parseInt(e.target.dataset.moduleIndex);
      goToModule(moduleIndex);
    });
  });

  // Клики по элементам списка модулей
  document.querySelectorAll(".module-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      const moduleIndex = parseInt(e.currentTarget.dataset.moduleIndex);
      goToModule(moduleIndex);
    });
  });
}

// Настройка обработчиков событий для нижней навигации
function setupBottomNavigationEvents() {
  // Кнопки навигации
  document
    .getElementById("prev-btn")
    .addEventListener("click", goToPreviousModule);
  document.getElementById("next-btn").addEventListener("click", goToNextModule);

  // Добавляем клавиатурную навигацию
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      goToPreviousModule();
    } else if (e.key === "ArrowRight") {
      goToNextModule();
    }
  });
}

// Переход к предыдущему модулю
function goToPreviousModule() {
  if (currentModuleIndex > 0) {
    goToModule(currentModuleIndex - 1);
  }
}

// Переход к следующему модулю
function goToNextModule() {
  if (currentModuleIndex < courseData.modules.length - 1) {
    goToModule(currentModuleIndex + 1);
  }
}

// Переход к конкретному модулю
function goToModule(moduleIndex) {
  if (moduleIndex >= 0 && moduleIndex < courseData.modules.length) {
    currentModuleIndex = moduleIndex;
    renderModule(courseData.modules[moduleIndex]);
    updateNavigationUI();
  }
}

// Обновление UI навигации
function updateNavigationUI() {
  // Обновляем верхнюю навигацию
  const moduleCounter = document.getElementById("module-counter");
  if (moduleCounter) {
    moduleCounter.textContent = `Модуль ${currentModuleIndex + 1} из ${courseData.modules.length}`;
  }

  // Обновляем точки прогресса
  document.querySelectorAll(".progress-dot").forEach((dot, index) => {
    dot.classList.toggle("active", index === currentModuleIndex);
  });

  // Обновляем список модулей
  document.querySelectorAll(".module-item").forEach((item, index) => {
    item.classList.toggle("active", index === currentModuleIndex);
  });

  // Обновляем нижние кнопки навигации
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");

  if (prevBtn && nextBtn) {
    prevBtn.disabled = currentModuleIndex === 0;
    nextBtn.disabled = currentModuleIndex === courseData.modules.length - 1;

    // Добавляем информацию о модулях в кнопки (опционально)
    if (currentModuleIndex > 0) {
      const prevModule = courseData.modules[currentModuleIndex - 1];
      prevBtn.title = `Перейти к: ${prevModule.title}`;
    }

    if (currentModuleIndex < courseData.modules.length - 1) {
      const nextModule = courseData.modules[currentModuleIndex + 1];
      nextBtn.title = `Перейти к: ${nextModule.title}`;
    }
  }
}

// Основная функция рендеринга модуля
export function renderModule(moduleData) {
  const app = document.getElementById("app");
  app.innerHTML = ""; // Очищаем контейнер

  // 1. Создаем заголовок модуля
  const header = document.createElement("div");
  header.className = "module-header";
  header.innerHTML = `
    <div class="module-order">Модуль ${moduleData.order + 1}</div>
    <h1 class="module-title">${moduleData.title}</h1>
    <p class="module-description">${moduleData.description}</p>
  `;
  app.appendChild(header);

  // 2. Создаем контейнер для блоков
  const container = document.createElement("div");
  container.className = "container";

  // 3. Для КАЖДОГО блока в массиве content_blocks
  moduleData.content_blocks.forEach((block, index) => {
    const blockElement = createContentBlock(block, index); // Создаем элемент блока
    container.appendChild(blockElement);
  });

  app.appendChild(container);
  window.scrollTo(0, 0);

  // Обновляем нижнюю навигацию (если она существует)
  updateNavigationUI();
}

// Функция создания блока контента (без изменений)
export function createContentBlock(block, index) {
  const blockElement = document.createElement("div");
  blockElement.className = "content-block";
  blockElement.id = `block-${index}`;
  blockElement.dataset.blockIndex = index;

  const typeLabel = document.createElement("div");
  typeLabel.className = "content-type-label";
  typeLabel.textContent = getContentTypeLabel(block.content_type);
  blockElement.appendChild(typeLabel);

  switch (block.content_type) {
    case "text":
      renderTextContent(blockElement, block);
      break;
    case "video":
      renderVideoContent(blockElement, block);
      break;
    case "code":
      renderCodeContent(blockElement, block);
      break;
    case "quiz":
      renderQuizContent(blockElement, block);
      break;
    case "mermaid":
      renderMermaidContent(blockElement, block);
      break;
  }

  if (block.ai_generated) {
    const aiMarker = document.createElement("div");
    aiMarker.className = "ai-generated";
    aiMarker.textContent = "Сгенерировано ИИ";
    blockElement.appendChild(aiMarker);
  }

  return blockElement;
}
