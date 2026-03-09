function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatDuration(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function formatTime(seconds) {
  // Если уже отформатировано
  if (typeof seconds === "string" && seconds.includes(":")) {
    return seconds;
  }

  // Конвертируем в число
  const secondsNum =
    typeof seconds === "string" ? parseInt(seconds, 10) : seconds;

  // Проверка на корректность
  if (isNaN(secondsNum) || !isFinite(secondsNum)) {
    return "0:00";
  }

  const mins = Math.floor(secondsNum / 60);
  const secs = secondsNum % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function parseMarkdown(markdown) {
  if (!markdown) return "";

  let result = markdown;

  // Обработка заголовков
  result = result.replace(/^# (.*$)/gm, "<h1>$1</h1>");
  result = result.replace(/^## (.*$)/gm, "<h2>$1</h2>");
  result = result.replace(/^### (.*$)/gm, "<h3>$1</h3>");
  result = result.replace(/^#### (.*$)/gm, "<h4>$1</h4>");

  // Горизонтальная линия
  result = result.replace(/^---$/gm, "<hr>");

  // Блок кода
  result = result.replace(/```[\s\S]*?```/g, (match) => {
    const code = match.replace(/```(\w+)?\n?/g, "").replace(/```/g, "");
    return `<pre><code>${escapeHtml(code)}</code></pre>`;
  });

  // Встроенный код
  result = result.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Жирный текст
  result = result.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  result = result.replace(/__([^_]+)__/g, "<strong>$1</strong>");

  // Курсив
  result = result.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  result = result.replace(/_([^_]+)_/g, "<em>$1</em>");

  // Списки
  const lines = result.split("\n");
  let inList = false;
  let listType = "";
  let listContent = "";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.match(/^\s*[-*+]\s+/)) {
      if (!inList) {
        inList = true;
        listType = "ul";
        listContent = "<ul>";
      }
      const item = line.replace(/^\s*[-*+]\s+/, "");
      listContent += `<li>${item.trim()}</li>`;
      lines[i] = "";
    } else if (line.match(/^\s*\d+\.\s+/)) {
      if (!inList) {
        inList = true;
        listType = "ol";
        listContent = "<ol>";
      }
      const item = line.replace(/^\s*\d+\.\s+/, "");
      listContent += `<li>${item.trim()}</li>`;
      lines[i] = "";
    } else {
      if (inList) {
        listContent += `</${listType}>`;
        lines[i - 1] = (lines[i - 1] || "") + listContent;
        inList = false;
        listType = "";
        listContent = "";
      }
    }
  }

  if (inList) {
    listContent += `</${listType}>`;
    lines[lines.length - 1] = (lines[lines.length - 1] || "") + listContent;
  }

  result = lines.join("\n");

  // Блоки цитат
  result = result.replace(/^>\s+(.*)$/gm, "<blockquote>$1</blockquote>");

  // Таблицы
  result = result.replace(
    /(\|[^\n]+\|\n)((?:\|[^\n]+\|\n?)+)/g,
    (match, header, rows) => {
      const headerCells = header
        .trim()
        .slice(1, -1)
        .split("|")
        .map((cell) => `<th>${cell.trim()}</th>`)
        .join("");

      const bodyRows = rows
        .trim()
        .split("\n")
        .map((row) => {
          const cells = row
            .trim()
            .slice(1, -1)
            .split("|")
            .map((cell) => `<td>${cell.trim()}</td>`)
            .join("");
          return `<tr>${cells}</tr>`;
        })
        .join("");

      return `<table><thead><tr>${headerCells}</tr></thead><tbody>${bodyRows}</tbody></table>`;
    },
  );

  // Ссылки
  result = result.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank">$1</a>',
  );

  // Изображения
  result = result.replace(
    /!\[([^\]]*)\]\(([^)]+)\)/g,
    '<img src="$2" alt="$1">',
  );

  // Обработка параграфов
  const finalLines = result.split("\n");
  let inParagraph = false;
  let paragraphContent = "";
  let finalResult = "";

  for (let i = 0; i < finalLines.length; i++) {
    const line = finalLines[i].trim();

    if (line === "") {
      if (inParagraph) {
        finalResult += `<p>${paragraphContent}</p>`;
        inParagraph = false;
        paragraphContent = "";
      }
      continue;
    }

    if (
      line.match(/^<(\w+)(\s|>)/) ||
      line.match(/^<\/\w+>/) ||
      line.match(/^<(h[1-6]|ul|ol|li|table|tr|td|th|blockquote|pre|code|hr)/)
    ) {
      if (inParagraph) {
        finalResult += `<p>${paragraphContent}</p>`;
        inParagraph = false;
        paragraphContent = "";
      }
      finalResult += line + "\n";
    } else {
      if (!inParagraph) {
        inParagraph = true;
        paragraphContent = line;
      } else {
        paragraphContent += " " + line;
      }
    }
  }

  if (inParagraph) {
    finalResult += `<p>${paragraphContent}</p>`;
  }

  return finalResult;
}

function getEmbedUrl(url, platform) {
  if (platform === "RuTube") {
    const videoId = url.match(/\/video\/([a-f0-9]+)\//);
    if (videoId) {
      return `https://rutube.ru/play/embed/${videoId[1]}`;
    }
  }
  return url;
}

function sanitizeMermaid(code) {
  let clean = code
    .replace(/^```\s*mermaid\s*\n?/i, "") // удаляем открывающий блок
    .replace(/```\s*$/i, "") // удаляем закрывающий блок
    .trim();

  // Удаляем директивы вида %%{...}%%
  clean = clean.replace(/^%%\{[\s\S]*?\}%%\s*\n?/gm, "");

  // Заменяем длинные тире (en-dash, em-dash) на обычный дефис во всём тексте
  clean = clean.replace(/\u2013|\u2014/g, "-");

  // Преобразуем "diagram" в "graph" (если используется)
  clean = clean.replace(/^(diagram)\s+(LR|RL|TB|BT|TD|DT)/gi, "graph $2");
  if (clean.toLowerCase().startsWith("diagram ")) {
    clean = "graph " + clean.substring(8);
  } else if (clean.toLowerCase().startsWith("diagram\n")) {
    clean = "graph" + clean.substring(7);
  }

  // Экранирование специальных символов внутри текста узлов (в квадратных скобках)
  clean = clean.replace(/\[([^\]]+)\]/g, (match, text) => {
    if (!text.match(/&#\d+;/g)) {
      // не экранируем уже экранированное
      const escapedText = text
        .replace(/\(/g, "&#40;")
        .replace(/\)/g, "&#41;")
        .replace(/\[/g, "&#91;")
        .replace(/\]/g, "&#93;")
        .replace(/\{/g, "&#123;")
        .replace(/\}/g, "&#125;")
        .replace(/\#/g, "&#35;")
        .replace(/\;/g, "&#59;")
        .replace(/\+/g, "&#43;")
        .replace(/\=/g, "&#61;")
        .replace(/,/g, "&#44;")
        .replace(/:/g, "&#58;");
      return `[${escapedText}]`;
    }
    return match;
  });

  // Удаляем возможные пустые строки в начале
  clean = clean.replace(/^\s*\n+/, "");
  return clean.trim();
}

function getContentTypeLabel(type) {
  const labels = {
    text: "📝 Теория",
    video: "🎥 Видео",
    code: "💻 Практика",
    quiz: "🧠 Проверка знаний",
    mermaid: "📊 Диаграмма",
  };
  return labels[type] || type;
}

function getModuleById(moduleId, course) {
  return course.modules.find((module) => module.id === moduleId);
}

export {
  formatTime,
  formatDuration,
  parseMarkdown,
  getEmbedUrl,
  sanitizeMermaid,
  getContentTypeLabel,
  getModuleById,
};
