// Подгоняет высоту поля ввода под текст: без пустого скролла на старте,
// скролл появляется только когда текст длиннее maxHeight.
export function autosizeTextarea(element, maxHeight = 180) {
  if (!element) return;
  element.style.height = "auto";
  const borders = element.offsetHeight - element.clientHeight;
  const contentHeight = element.scrollHeight + borders;
  element.style.height = `${Math.min(contentHeight, maxHeight)}px`;
  element.style.overflowY = contentHeight > maxHeight ? "auto" : "hidden";
}
