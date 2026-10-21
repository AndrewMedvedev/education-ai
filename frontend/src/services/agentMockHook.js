// Точка подключения локального демо-режима ИИ-агентов.
// Сам демо-режим (services/agentMock.local.js) не хранится в репозитории и
// подключается только в dev-сборке, если файл есть у разработчика локально.
// Без файла все функции ниже безопасно возвращают «выключено».
const modules = import.meta.env.DEV
  ? import.meta.glob("./agentMock.local.js", { eager: true })
  : {};
const localMock = Object.values(modules)[0] || null;

export function isAgentMockEnabled() {
  return Boolean(localMock?.isAgentMockEnabled?.());
}

export function mockInterviewer(kind, payload) {
  if (!localMock) throw new Error("Демо-режим ИИ недоступен.");
  return localMock.mockInterviewer(kind, payload);
}
