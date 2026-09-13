function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function printLessonSummary({ course, block, lesson }) {
  const printWindow = window.open("", "_blank");

  if (!printWindow) {
    window.alert("Разрешите всплывающие окна, чтобы сохранить конспект в PDF.");
    return;
  }

  const lessonContent = lesson.markdown || lesson.content || "Материал урока пока пуст.";
  const documentTitle = `${course.title} — ${lesson.title}`;

  printWindow.document.write(`<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(documentTitle)}</title>
    <style>
      @page { size: A4; margin: 18mm; }
      body { color: #24211d; font: 14px/1.65 Arial, sans-serif; }
      header { border-bottom: 1px solid #d8cfc1; margin-bottom: 24px; padding-bottom: 16px; }
      small { color: #746b60; }
      h1 { font-size: 24px; line-height: 1.25; margin: 8px 0; }
      h2 { font-size: 16px; margin: 0; color: #5e4d5e; }
      pre { white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; }
      footer { border-top: 1px solid #d8cfc1; color: #746b60; margin-top: 28px; padding-top: 12px; }
    </style>
  </head>
  <body>
    <header>
      <small>${escapeHtml(course.title)} · ${escapeHtml(block.title)}</small>
      <h1>${escapeHtml(lesson.title)}</h1>
      <h2>Конспект урока</h2>
    </header>
    <pre>${escapeHtml(lessonContent)}</pre>
    <footer>Создано в AI Course Lab</footer>
    <script>window.addEventListener("load", () => window.print());</script>
  </body>
</html>`);
  printWindow.document.close();
}
