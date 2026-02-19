import {
  renderCodeContent,
  renderMermaidContent,
  renderQuizContent,
  renderTextContent,
  renderVideoContent,
} from "./render.js";

import { getContentTypeLabel } from "./utils.js";

// Основная функция рендеринга модуля
export function renderModule(moduleData) {
  const app = document.getElementById("app");
  app.innerHTML = ""; // Очищаем контейнер

  const container = document.createElement("div");
  container.className = "container";

  // 3. Для КАЖДОГО блока в массиве content_blocks
  moduleData.forEach((block, index) => {
    const blockElement = createContentBlock(block, index); // Создаем элемент блока
    container.appendChild(blockElement);
  });

  app.appendChild(container);
  window.scrollTo(0, 0);
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
