// Тoggle темы
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Обновляем иконку кнопки темы
    const themeBtn = document.querySelector('.theme-btn');
    if (themeBtn) {
        const icon = themeBtn.querySelector('i');
        icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Инициализация темы при загрузке
document.addEventListener('DOMContentLoaded', function() {
    // Восстанавливаем тему из localStorage
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Устанавливаем правильную иконку темы
    const themeBtn = document.querySelector('.theme-btn');
    if (themeBtn) {
        const icon = themeBtn.querySelector('i');
        icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }

    // Обработка выпадающих меню
    initDropdowns();

    // Адаптивная навигация
    initResponsiveNav();
});

// Управление выпадающими меню
function initDropdowns() {
    document.addEventListener('click', function(e) {
        // Закрываем все выпадающие меню при клике вне их
        if (!e.target.closest('.dropdown-menu') && !e.target.closest('.user-menu-btn')) {
            document.querySelectorAll('.dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
        }

        // Переключение выпадающего меню пользователя
        if (e.target.closest('.user-menu-btn')) {
            const dropdown = e.target.closest('.user-menu').querySelector('.dropdown-menu');
            dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
        }
    });
}

// Адаптивная навигация
function initResponsiveNav() {
    const mobileToggle = document.getElementById('mobileToggle');

    if (mobileToggle) {
        mobileToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('active');
        });
    }

    // Закрытие боковой панели при клике на основной контент на мобильных
    document.querySelector('.main-content').addEventListener('click', function() {
        if (window.innerWidth <= 768) {
            document.querySelector('.sidebar').classList.remove('active');
        }
    });
}

// Уведомления и сообщения
function initNotifications() {
    const notificationBtn = document.querySelector('.notification-btn');
    const messageBtn = document.querySelector('.message-btn');

    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            // TODO: Реализовать попап уведомлений
            console.log('Открыть уведомления');
        });
    }

    if (messageBtn) {
        messageBtn.addEventListener('click', function() {
            // TODO: Реализовать попап сообщений
            console.log('Открыть сообщения');
        });
    }
}

// Помощник для показа уведомлений
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    // Анимация появления
    setTimeout(() => toast.classList.add('show'), 100);

    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}