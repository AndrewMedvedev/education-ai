import { chat } from "../general/rest.js";

let userId = null;
let courseId = null;

export function initializeChat(user_id, course_id) {
  userId = user_id;
  courseId = course_id;
  const chatToggle = document.getElementById("chatToggle");
  const chatClose = document.getElementById("chatClose");
  const chatInput = document.getElementById("chatInput");
  const chatSend = document.getElementById("chatSend");

  chatToggle?.addEventListener("click", toggleChat);
  chatClose?.addEventListener("click", closeChat);
  chatSend?.addEventListener("click", sendMessage);

  chatInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  chatInput?.addEventListener("input", autoResizeTextarea);
  initializeChatState();
}

function initializeChatState() {
  const isChatOpen = sessionStorage.getItem("isChatOpen");
  const chatToggle = document.getElementById("chatToggle");
  const chatPanel = document.getElementById("chatPanel");

  if (isChatOpen === "true") {
    chatPanel?.classList.add("open");
    document.body.classList.add("chat-open");
    if (chatToggle) chatToggle.style.display = "none";
  } else {
    chatPanel?.classList.remove("open");
    document.body.classList.remove("chat-open");
    if (chatToggle) chatToggle.style.display = "flex";
  }
}

function toggleChat() {
  const currentState = sessionStorage.getItem("isChatOpen") === "true";
  if (currentState) closeChat();
  else openChat();
}

function openChat() {
  const chatToggle = document.getElementById("chatToggle");
  const chatPanel = document.getElementById("chatPanel");
  const chatInput = document.getElementById("chatInput");

  chatPanel?.classList.add("open");
  document.body.classList.add("chat-open");
  if (chatToggle) chatToggle.style.display = "none";
  chatInput?.focus();

  sessionStorage.setItem("isChatOpen", "true");
  scrollToBottom();
}

function closeChat() {
  const chatToggle = document.getElementById("chatToggle");
  const chatPanel = document.getElementById("chatPanel");

  chatPanel?.classList.remove("open");
  document.body.classList.remove("chat-open");
  if (chatToggle) chatToggle.style.display = "flex";

  sessionStorage.setItem("isChatOpen", "false");
}

async function sendMessage() {
  const chatInput = document.getElementById("chatInput");
  const message = chatInput?.value.trim();
  const isTyping = sessionStorage.getItem("isTyping") === "true";

  if (!message || isTyping) return;

  addMessage(message, "user");

  if (chatInput) {
    chatInput.value = "";
    autoResizeTextarea();
  }

  showTypingIndicator();

  try {
    const response = await chat(userId, message, courseId);

    if (response.status === 429) {
      addMessage(
        "Ой, мы так увлеклись беседой, что потратили все сегодняшние сообщения! Возвращайся завтра.",
        "ai",
      );
    } else if (!response.ok) {
      addMessage(
        "Извините, произошла ошибка при получении ответа. Пожалуйста, попробуйте позже.",
        "ai",
      );
    }
    const result = await response.json();

    // Убираем индикатор печатания
    hideTypingIndicator();

    // Добавляем ответ ИИ
    addMessage(result.text, "ai");
  } catch (error) {
    console.error("Error getting AI response:", error);
    hideTypingIndicator();
  }
}

function addMessage(text, sender) {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  const messageDiv = document.createElement("div");
  messageDiv.className = `chat-message ${sender}-message`;
  messageDiv.innerHTML = formatMessage(text);
  chatMessages.appendChild(messageDiv);
  scrollToBottom();
}

// ================== MARKDOWN RENDERER ==================
function formatMessage(text) {
  // Если markdown-it не загружен – возвращаем экранированный текст с <br>
  if (typeof window.markdownit !== "function") {
    console.warn("markdown-it not loaded, fallback to plain text");
    return escapeHtml(text).replace(/\n/g, "<br>");
  }

  const md = window.markdownit({
    html: false,
    linkify: true,
    typographer: true,
    highlight: function (code, lang) {
      if (lang && window.hljs && window.hljs.getLanguage(lang)) {
        try {
          return (
            '<pre><code class="hljs language-' +
            lang +
            '">' +
            window.hljs.highlight(code, { language: lang }).value +
            "</code></pre>"
          );
        } catch (__) {}
      }
      return "<pre><code>" + escapeHtml(code) + "</code></pre>";
    },
  });

  // Подключаем GFM-плагин, если он загружен
  if (window.markdownitGfm) {
    md.use(window.markdownitGfm);
  } else {
    console.warn(
      "markdown-it-gfm not loaded, tables & strikethrough won't work",
    );
  }

  // Подключаем KaTeX-плагин, если загружен
  if (window.markdownitKatex) {
    md.use(window.markdownitKatex, {
      throwOnError: false,
      output: "html",
    });
  } else {
    console.warn("markdown-it-katex not loaded, LaTeX formulas won't render");
  }

  let rawHtml = md.render(text);

  // Очистка через DOMPurify
  if (window.DOMPurify) {
    rawHtml = window.DOMPurify.sanitize(rawHtml, {
      USE_PROFILES: { html: true },
    });
  } else {
    console.warn("DOMPurify not loaded, HTML may be unsafe");
  }

  return rawHtml;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
function showTypingIndicator() {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;
  sessionStorage.setItem("isTyping", "true");
  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  indicator.id = "typingIndicator";
  for (let i = 0; i < 3; i++)
    indicator.appendChild(document.createElement("span"));
  chatMessages.appendChild(indicator);
  scrollToBottom();
}

function hideTypingIndicator() {
  sessionStorage.setItem("isTyping", "false");
  document.getElementById("typingIndicator")?.remove();
}

function scrollToBottom() {
  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
}

function autoResizeTextarea() {
  const chatInput = document.getElementById("chatInput");
  if (!chatInput) return;
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
}
