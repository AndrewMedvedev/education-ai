export function initializeChat() {
  const chatToggle = document.getElementById("chatToggle");
  const chatClose = document.getElementById("chatClose");
  const chatInput = document.getElementById("chatInput");
  const chatSend = document.getElementById("chatSend");

  chatToggle?.addEventListener("click", toggleChat);
  chatClose?.addEventListener("click", closeChat);
  chatSend?.addEventListener("click", sendMessage);

  // Отправка по Enter (но Shift+Enter для новой строки)
  chatInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Автоматическое изменение высоты textarea
  chatInput?.addEventListener("input", autoResizeTextarea);

  // Инициализация состояния чата при загрузке
  initializeChatState();
}

// Инициализация состояния чата
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

// Переключение чата
function toggleChat() {
  const currentState = sessionStorage.getItem("isChatOpen") === "true";

  if (currentState) {
    closeChat();
  } else {
    openChat();
  }
}

// Открытие чата
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

// Закрытие чата
function closeChat() {
  const chatToggle = document.getElementById("chatToggle");
  const chatPanel = document.getElementById("chatPanel");

  chatPanel?.classList.remove("open");
  document.body.classList.remove("chat-open");
  if (chatToggle) chatToggle.style.display = "flex";

  sessionStorage.setItem("isChatOpen", "false");
}

// Отправка сообщения
async function sendMessage() {
  const chatInput = document.getElementById("chatInput");
  const message = chatInput?.value.trim();
  const isTyping = sessionStorage.getItem("isTyping") === "true";

  if (!message || isTyping) return;

  // Добавляем сообщение пользователя
  addMessage(message, "user");

  // Очищаем input
  if (chatInput) {
    chatInput.value = "";
    autoResizeTextarea();
  }

  // Показываем индикатор печатания
  showTypingIndicator();

  try {
    // Здесь будет запрос к вашему API ИИ
    const response = await getAIResponse(message);

    // Убираем индикатор печатания
    hideTypingIndicator();

    // Добавляем ответ ИИ
    addMessage(response, "ai");
  } catch (error) {
    console.error("Error getting AI response:", error);

    // Убираем индикатор печатания
    hideTypingIndicator();

    // Показываем сообщение об ошибке
    addMessage(
      "Извините, произошла ошибка при получении ответа. Пожалуйста, попробуйте позже.",
      "ai",
    );
  }
}

// Добавление сообщения в чат
function addMessage(text, sender) {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  const messageDiv = document.createElement("div");
  messageDiv.className = `chat-message ${sender}-message`;

  // Поддержка markdown-like форматирования
  const formattedText = formatMessage(text);
  messageDiv.innerHTML = formattedText;

  chatMessages.appendChild(messageDiv);
  scrollToBottom();
}

// Форматирование сообщения (простой markdown)
function formatMessage(text) {
  // Экранируем HTML
  text = escapeHtml(text);

  // Заменяем переносы строк на <br>
  text = text.replace(/\n/g, "<br>");

  // Жирный текст
  text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Курсив
  text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Код
  text = text.replace(/`(.*?)`/g, "<code>$1</code>");

  // Блоки кода
  text = text.replace(/```(.*?)```/gs, (match, code) => {
    return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
  });

  return text;
}

// Экранирование HTML
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Показать индикатор печатания
function showTypingIndicator() {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  sessionStorage.setItem("isTyping", "true");

  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  indicator.id = "typingIndicator";

  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("span");
    indicator.appendChild(dot);
  }

  chatMessages.appendChild(indicator);
  scrollToBottom();
}

// Скрыть индикатор печатания
function hideTypingIndicator() {
  sessionStorage.setItem("isTyping", "false");

  const indicator = document.getElementById("typingIndicator");
  if (indicator) {
    indicator.remove();
  }
}

// Прокрутка вниз
function scrollToBottom() {
  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

// Автоматическое изменение высоты textarea
function autoResizeTextarea() {
  const chatInput = document.getElementById("chatInput");
  if (!chatInput) return;

  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
}

// Получение ответа от ИИ (заглушка)
async function getAIResponse(message) {
  // Здесь должен быть ваш API запрос
  // Это просто заглушка для демонстрации

  await new Promise((resolve) => setTimeout(resolve, 1500));

  // Примеры ответов на основе контекста курса
  const responses = [
    "Я могу помочь вам с этим вопросом! Давайте разберем тему подробнее.",
    "Отличный вопрос! В контексте нашего курса это объясняется следующим образом...",
    "Вот пример кода, который иллюстрирует ваш вопрос:\n```python\ndef example():\n    print('Hello, World!')\n```",
    "Рекомендую обратить внимание на видео-материалы в этом модуле, там подробно раскрыта эта тема.",
    "Это фундаментальный концепт. Если хотите, могу объяснить его более подробно или привести аналогию.",
  ];

  return responses[Math.floor(Math.random() * responses.length)];
}
