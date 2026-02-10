import {
  parseMarkdown,
  formatDuration,
  formatTime,
  getEmbedUrl,
  sanitizeMermaid,
} from "./utils.js";
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
});

function validateContainer(container) {
  if (!(container instanceof HTMLElement)) {
    console.error("Invalid container element");
    return false;
  }
  return true;
}

function renderTextContent(container, content) {
  if (!validateContainer(container)) return;

  const contentDiv = document.createElement("div");
  contentDiv.className = "text-content";

  // Безопасная обработка markdown
  const parsedContent = parseMarkdown(content.md_content || "");
  contentDiv.innerHTML = parsedContent;

  container.appendChild(contentDiv);
}

function renderVideoContent(container, content) {
  if (!validateContainer(container)) return;

  if (!content?.url) {
    console.error("Invalid video content: URL is required");
    return;
  }

  const videoDiv = document.createElement("div");
  videoDiv.className = "video-content";

  // Контейнер для видео
  const videoContainer = document.createElement("div");
  videoContainer.className = "video-container";

  const iframe = document.createElement("iframe");
  iframe.src = getEmbedUrl(content.url, content.platform);
  iframe.setAttribute(
    "allow",
    "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture",
  );
  iframe.setAttribute("allowfullscreen", "");
  iframe.setAttribute("loading", "lazy");
  iframe.setAttribute("title", `Видео: ${content.title || "Без названия"}`);

  videoContainer.appendChild(iframe);
  videoDiv.appendChild(videoContainer);

  // Мета-информация
  const metaDiv = document.createElement("div");
  metaDiv.className = "video-meta";

  const platformSpan = document.createElement("span");
  platformSpan.className = "video-platform";
  platformSpan.textContent = content.platform || "YouTube";
  metaDiv.appendChild(platformSpan);

  if (content.duration_seconds && content.duration_seconds > 0) {
    const durationSpan = document.createElement("span");
    durationSpan.className = "video-duration";
    durationSpan.textContent = formatDuration(content.duration_seconds);
    metaDiv.appendChild(durationSpan);
  }

  videoDiv.appendChild(metaDiv);

  // Ключевые моменты
  if (content.key_moments && Object.keys(content.key_moments).length > 0) {
    const keyMomentsDiv = document.createElement("div");
    keyMomentsDiv.className = "key-moments";

    const heading = document.createElement("h4");
    heading.textContent = "Ключевые моменты";
    keyMomentsDiv.appendChild(heading);

    Object.entries(content.key_moments).forEach(([time, description]) => {
      const momentDiv = document.createElement("div");
      momentDiv.className = "key-moment-item";

      const timeSpan = document.createElement("span");
      timeSpan.className = "key-moment-time";
      timeSpan.textContent = formatTime(time);

      const descSpan = document.createElement("span");
      descSpan.className = "key-moment-desc";
      descSpan.textContent = description;

      momentDiv.appendChild(timeSpan);
      momentDiv.appendChild(descSpan);
      keyMomentsDiv.appendChild(momentDiv);
    });

    videoDiv.appendChild(keyMomentsDiv);
  }

  // Вопросы для обсуждения
  if (content.discussion_questions && content.discussion_questions.length > 0) {
    const questionsDiv = document.createElement("div");
    questionsDiv.className = "discussion-questions";

    const heading = document.createElement("h4");
    heading.textContent = "Вопросы для обсуждения";
    questionsDiv.appendChild(heading);

    content.discussion_questions.forEach((question) => {
      const questionDiv = document.createElement("div");
      questionDiv.className = "question-item";
      questionDiv.textContent = question;
      questionsDiv.appendChild(questionDiv);
    });

    videoDiv.appendChild(questionsDiv);
  }

  container.appendChild(videoDiv);
}

async function renderMermaidContent(container, content) {
  if (!container || !content?.mermaid_code) return;

  const wrapper = document.createElement("div");
  wrapper.className = "mermaid-block";

  if (content.title) {
    const titleEl = document.createElement("h3");
    titleEl.textContent = content.title;
    wrapper.appendChild(titleEl);
  }

  const diagramContainer = document.createElement("div");
  diagramContainer.className = "mermaid";
  wrapper.appendChild(diagramContainer);
  container.appendChild(wrapper);

  try {
    // Очищаем код
    const cleanCode = sanitizeMermaid(content.mermaid_code);

    // !!! Очень важно — именно сюда кладем cleanCode
    diagramContainer.textContent = cleanCode;

    // Инициализация Mermaid (если еще не сделано)
    if (typeof mermaid === "undefined") {
      throw new Error("Mermaid не загружен");
    }
    mermaid.initialize({ startOnLoad: false });

    // Рендерим диаграмму через mermaid.run()
    await mermaid.run({
      nodes: [diagramContainer],
    });
  } catch (error) {
    diagramContainer.innerHTML =
      "<p class='mermaid-error'>Ошибка при рендеринге диаграммы</p>";
    console.error("Mermaid render error:", error);
    console.error("Code that failed:", content.mermaid_code);
  }

  if (content.explanation) {
    const explanationDiv = document.createElement("div");
    explanationDiv.className = "mermaid-explanation";
    explanationDiv.innerHTML = `<strong>Пояснение:</strong> ${content.explanation}`;
    wrapper.appendChild(explanationDiv);
  }
}

function renderQuizContent(container, content) {
  const questions = content.questions;
  if (!validateContainer(container)) return;

  if (!Array.isArray(questions)) {
    console.error("Invalid quiz content: expected array");
    return;
  }

  container.classList.add("quiz-block");

  questions.forEach((item, index) => {
    const [question, answer] = item;

    const questionDiv = document.createElement("div");
    questionDiv.className = "quiz-question";
    questionDiv.textContent = `${index + 1}. ${question}`;
    container.appendChild(questionDiv);

    const answerDiv = document.createElement("div");
    answerDiv.className = "quiz-answer hidden-answer";
    answerDiv.id = `answer-${index}`;

    answerDiv.innerHTML = `<strong>Ответ:</strong> ${answer}`;

    container.appendChild(answerDiv);

    const button = document.createElement("button");
    button.className = "show-answer-btn";
    button.type = "button";
    button.textContent = "Показать ответ";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", `answer-${index}`);

    button.addEventListener("click", () => {
      const answerEl = document.getElementById(`answer-${index}`);
      if (!answerEl) return;

      const isHidden = answerEl.classList.contains("hidden-answer");
      answerEl.classList.toggle("hidden-answer");
      button.textContent = isHidden ? "Скрыть ответ" : "Показать ответ";
      button.setAttribute("aria-expanded", String(!isHidden));
    });

    container.appendChild(button);
  });
}

function renderCodeContent(container, content) {
  if (!validateContainer(container)) return;

  if (!content?.code) {
    console.error("Invalid code content: code is required");
    return;
  }

  // Создаем основной блок кода
  const codeBlock = document.createElement("div");
  codeBlock.className = "code-block";

  // Создаем заголовок с языком и кнопкой копирования
  const headerDiv = document.createElement("div");
  headerDiv.className = "code-header";

  const languageLabel = document.createElement("span");
  languageLabel.className = "language-label";
  languageLabel.textContent = content.language || "text";
  headerDiv.appendChild(languageLabel);

  // Кнопка копирования
  const copyButton = document.createElement("button");
  copyButton.className = "copy-button";
  copyButton.innerHTML = `
    <svg class="copy-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
    </svg>
    <span class="copy-text">Копировать</span>
  `;

  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(content.code);

      // Визуальная обратная связь
      const originalText = copyButton.querySelector(".copy-text").textContent;
      copyButton.querySelector(".copy-text").textContent = "Скопировано!";
      copyButton.classList.add("copied");

      setTimeout(() => {
        copyButton.querySelector(".copy-text").textContent = originalText;
        copyButton.classList.remove("copied");
      }, 2000);
    } catch (err) {
      console.error("Failed to copy: ", err);
      // Fallback для старых браузеров
      const textArea = document.createElement("textarea");
      textArea.value = content.code;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);

      copyButton.querySelector(".copy-text").textContent =
        "Скопировано (fallback)";
      setTimeout(() => {
        copyButton.querySelector(".copy-text").textContent = "Копировать";
      }, 2000);
    }
  });

  headerDiv.appendChild(copyButton);
  codeBlock.appendChild(headerDiv);

  // Основной блок с кодом
  const codeDiv = document.createElement("pre");
  codeDiv.className = "code-content";

  const codeElement = document.createElement("code");

  // Всегда используем Prism.js для подсветки
  const language = content.language ? content.language.toLowerCase() : "text";
  codeElement.className = `language-${language}`;

  // Проверяем наличие Prism и подсвечиваем код
  if (typeof Prism !== "undefined") {
    // Получаем язык для Prism
    const prismLanguage = Prism.languages[language] || Prism.languages.text;
    codeElement.innerHTML = Prism.highlight(
      content.code,
      prismLanguage,
      language,
    );
  } else {
    // Если Prism не загружен, показываем обычный текст с экранированием
    codeElement.textContent = content.code;
    console.warn(
      "Prism.js не загружен. Код будет отображен без подсветки синтаксиса.",
    );
  }

  codeDiv.appendChild(codeElement);
  codeBlock.appendChild(codeDiv);

  // Пояснение к коду (если есть)
  if (content.explanation) {
    const explanationDiv = document.createElement("div");
    explanationDiv.className = "code-explanation";
    explanationDiv.innerHTML = `<strong>Пояснение:</strong> ${content.explanation}`;
    codeBlock.appendChild(explanationDiv);
  }

  container.appendChild(codeBlock);
}

export {
  renderTextContent,
  renderVideoContent,
  renderCodeContent,
  renderQuizContent,
  renderMermaidContent,
};
