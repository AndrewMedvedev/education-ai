// import { course } from "../../general/data.js";
import { getModuleById } from "../../general/utils.js";
import { sendData } from "../../general/rest.js";

const dataElement = document.getElementById("initial-data");
const data = JSON.parse(dataElement.textContent);
const baseURL = data[baseURL]
const moduleId = data[moduleId];
const course = data[course];

// const moduleId = "70601b76-7d82-4251-8409-055a3ccced00";
const module = getModuleById(moduleId, course);

let tests = [];
let currentEditId = null;
module.assignment.id = Date.now();
// Добавляем пример при загрузке
tests.push(module.assignment);

// Функция для отображения уведомлений
function showNotification(message, type = "success") {
  // Удаляем существующее уведомление, если есть
  const existingNotification = document.querySelector(".notification");
  if (existingNotification) {
    existingNotification.remove();
  }

  // Создаем новое уведомление
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;

  // Добавляем в DOM
  document.body.appendChild(notification);

  setTimeout(() => notification.classList.add("show"), 10);

  // Автоматически скрываем через 5 секунд
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => notification.remove(), 300);
  }, 5000);
}

// Функция для отправки данных на API
async function saveToAPI(moduleData) {
  try {
    delete moduleData.assignment.id;
    const moduleIndex = course.modules.findIndex(
      (module) => module.id === moduleId,
    );
    course.modules[moduleIndex].assignment = moduleData.assignment;
    const response = await sendData(course, baseURL);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.message ||
          `Ошибка ${response.status}: ${response.statusText}`,
      );
    }
  } catch (error) {
    console.error("API Error:", error);
    throw new Error(`Не удалось сохранить данные: ${error.message}`);
  }
}

// Функция для отрисовки списка тестов
function renderTests() {
  const container = document.getElementById("testsContainer");

  if (tests.length === 0) {
    container.innerHTML = `
            <div class="empty-state">
                <div>📭</div>
                <h3>Нет заданий</h3>
                <p>Создайте новое задание с помощью формы выше</p>
            </div>
        `;
    return;
  }

  container.innerHTML = tests
    .map(
      (test) => `
                <div class="test-card">
                    <h3>${escapeHtml(test.title)}</h3>
                    <div class="meta">
                        <span>🎯 Макс: ${test.max_score}</span>
                        <span>✅ Проходной: ${test.passing_score}</span>
                        <span>🌿 Ветка: ${test.required_branch}</span>
                        <span class="badge badge-success">v${test.version}</span>
                    </div>
                    <div class="repository-info">
                        <div>📦 Задание: <a href="${test.repository_task}" target="_blank">${test.repository_task}</a></div>
                        <div>📋 Правила: <a href="${test.repository_rules}" target="_blank">${test.repository_rules}</a></div>
                    </div>
                    <div class="card-actions">
                        <button class="edit-btn" onclick="editTest('${test.id}')">
                            <span>✏️</span> Ред.
                        </button>
                        <button class="delete-btn" onclick="deleteTest('${test.id}')">
                            <span>🗑️</span> Уд.
                        </button>
                    </div>
                </div>
            `,
    )
    .join("");
}

// Экранирование HTML для безопасности
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Функция для заполнения формы данными теста
function fillForm(test) {
  document.getElementById("title").value = test.title || "";
  document.getElementById("max_score").value = test.max_score || 100;
  document.getElementById("passing_score").value = test.passing_score || 70;
  document.getElementById("repository_task").value = test.repository_task || "";
  document.getElementById("repository_rules").value =
    test.repository_rules || "";
  document.getElementById("required_branch").value =
    test.required_branch || "develop";
  document.getElementById("version").value = test.version || 0;
  document.getElementById("editId").value = test.id || "";

  document.getElementById("formTitle").textContent = "Редактировать задание";
  document.getElementById("submitBtn").innerHTML =
    "<span>🔄</span> Обновить задание";
}

// Функция для очистки формы
function clearForm() {
  document.getElementById("testForm").reset();
  document.getElementById("editId").value = "";
  document.getElementById("version").value = "0";
  document.getElementById("title").value = "";
  document.getElementById("repository_task").value = "";
  document.getElementById("repository_rules").value = "";
  document.getElementById("required_branch").value = "develop";
  document.getElementById("max_score").value = "100";
  document.getElementById("passing_score").value = "70";

  document.getElementById("formTitle").textContent = "Создать новое задание";
  document.getElementById("submitBtn").innerHTML =
    "<span>💾</span> Сохранить задание";
  currentEditId = null;
}

// Функция отмены редактирования
window.cancelEdit = function () {
  clearForm();
};

// Функция редактирования теста
window.editTest = function (id) {
  const test = tests.find((t) => t.id == id);
  if (test) {
    fillForm(test);
    currentEditId = id;
  }
};

// Функция удаления теста
window.deleteTest = async function (id) {
  if (!confirm("Вы уверены, что хотите удалить это задание?")) {
    return;
  }

  // Блокируем кнопки удаления на время операции
  const deleteButtons = document.querySelectorAll(".delete-btn");
  deleteButtons.forEach((btn) => (btn.disabled = true));

  try {
    // Удаляем тест из локального массива
    tests = tests.filter((t) => t.id != id);

    // Обновляем данные модуля
    const updatedModule = { ...module };
    updatedModule.assignment =
      tests.find((t) => t.id === module.assignment?.id) || tests[0] || null;

    // Перерисовываем список
    renderTests();

    // Если удаляем текущий редактируемый тест, очищаем форму
    if (currentEditId == id) {
      clearForm();
    }

    showNotification("Задание успешно удалено!", "success");
  } catch (error) {
    showNotification(error.message, "error");
  } finally {
    // Разблокируем кнопки
    deleteButtons.forEach((btn) => (btn.disabled = false));
  }
};

// Обработчик отправки формы
document
  .getElementById("testForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    // Блокируем кнопку отправки
    const submitBtn = document.getElementById("submitBtn");
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = "<span>⏳</span> Сохранение...";

    try {
      // Собираем данные из формы
      const testData = {
        id: document.getElementById("editId").value || Date.now().toString(),
        assignment_type: "github",
        version: parseInt(document.getElementById("version").value) || 0,
        title: document.getElementById("title").value,
        max_score: parseInt(document.getElementById("max_score").value),
        passing_score: parseInt(document.getElementById("passing_score").value),
        repository_task: document.getElementById("repository_task").value,
        repository_rules: document.getElementById("repository_rules").value,
        required_branch: document.getElementById("required_branch").value,
      };

      // Валидация
      if (testData.passing_score > testData.max_score) {
        showNotification(
          "Проходной балл не может быть больше максимального!",
          "error",
        );
        return;
      }

      // Проверяем обязательные поля
      if (
        !testData.title ||
        !testData.repository_task ||
        !testData.repository_rules
      ) {
        showNotification(
          "Пожалуйста, заполните все обязательные поля!",
          "error",
        );
        return;
      }

      // Проверяем, редактирование это или создание
      const existingIndex = tests.findIndex((t) => t.id == testData.id);
      const isEditing = existingIndex !== -1;

      if (isEditing) {
        // Обновляем существующий тест
        testData.version = tests[existingIndex].version + 1;
        tests[existingIndex] = testData;
      } else {
        // Добавляем новый тест
        tests.push(testData);
      }

      // Обновляем assignment в модуле
      const updatedModule = { ...module };
      updatedModule.assignment =
        tests.find((t) => t.id === module.assignment?.id) ||
        tests[tests.length - 1];

      // Отправляем на API
      await saveToAPI(updatedModule);

      // Перерисовываем список
      renderTests();

      // Очищаем форму
      clearForm();

      // Показываем сообщение об успехе
      showNotification(
        isEditing ? "Задание успешно обновлено!" : "Задание успешно создано!",
        "success",
      );
    } catch (error) {
      showNotification(error.message, "error");
    } finally {
      // Разблокируем кнопку и восстанавливаем текст
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });

// Добавляем стили для уведомлений
const style = document.createElement("style");
style.textContent = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .notification.show {
        opacity: 1;
        transform: translateX(0);
    }
    
    .notification-success {
        background: linear-gradient(135deg, #28a745, #20c997);
    }
    
    .notification-error {
        background: linear-gradient(135deg, #dc3545, #c82333);
    }
    
    button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
`;

document.head.appendChild(style);

// Инициализация
renderTests();
