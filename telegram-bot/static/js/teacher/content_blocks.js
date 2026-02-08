document.addEventListener('DOMContentLoaded', function() {
    // Инициализация highlight.js для подсветки синтаксиса
    hljs.highlightAll();

    // Инициализация Mermaid
    mermaid.initialize({
        startOnLoad: false,
        theme: document.body.classList.contains('dark-mode') ? 'dark' : 'default',
        securityLevel: 'loose',
        flowchart: { useMaxWidth: false },
        sequence: { useMaxWidth: false }
    });

    // Рендер Mermaid диаграмм
    renderMermaidDiagrams();

    // Инициализация отслеживания прогресса
    initProgressTracker();

    // Инициализация кнопок копирования кода
    initCopyButtons();

    // Инициализация обработчиков для показа ответов
    initQuizHandlers();
});

function renderMermaidDiagrams() {
    const diagrams = document.querySelectorAll('.mermaid-diagram');
    diagrams.forEach((diagram, index) => {
        const mermaidCode = diagram.dataset.mermaid;
        if (mermaidCode) {
            try {
                mermaid.render(`mermaid-diagram-${index}`, mermaidCode, (svgCode) => {
                    diagram.innerHTML = svgCode;

                    // Добавляем обработчик клика для зума
                    diagram.querySelector('svg')?.addEventListener('click', function() {
                        toggleMermaidFullscreen(this.closest('.mermaid-container'));
                    });
                });
            } catch (error) {
                console.error('Mermaid render error:', error);
                diagram.innerHTML = `
                    <div class="mermaid-error">
                        <p>Ошибка при отображении диаграммы:</p>
                        <pre>${error.message}</pre>
                        <button onclick="retryMermaid(this)">Повторить</button>
                    </div>
                `;
            }
        }
    });
}

function initProgressTracker() {
    const blocks = document.querySelectorAll('.content-block-wrapper');
    const totalBlocks = blocks.length;
    let viewedBlocks = new Set();

    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('#progress-value');

    function updateProgress() {
        const progress = Math.round((viewedBlocks.size / totalBlocks) * 100);
        progressBar.style.setProperty('--progress-width', `${progress}%`);
        progressText.textContent = progress;

        // Сохраняем прогресс в localStorage
        localStorage.setItem('content_previewer_progress', progress);
    }

    // Восстанавливаем прогресс из localStorage
    const savedProgress = localStorage.getItem('content_previewer_progress');
    if (savedProgress) {
        progressText.textContent = savedProgress;
        progressBar.style.setProperty('--progress-width', `${savedProgress}%`);
    }

    // Отслеживаем видимость блоков
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const blockId = entry.target.dataset.blockIndex ||
                               Array.from(blocks).indexOf(entry.target);
                viewedBlocks.add(blockId);
                updateProgress();
            }
        });
    }, {
        threshold: 0.5
    });

    blocks.forEach((block, index) => {
        block.dataset.blockIndex = index;
        observer.observe(block);
    });
}

function initCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const codeBlock = this.closest('.code-container').querySelector('code');
            const code = codeBlock.textContent;

            navigator.clipboard.writeText(code).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="icon-check"></i> Скопировано!';
                this.style.background = '#10b981';

                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.style.background = '';
                }, 2000);
            }).catch(err => {
                console.error('Ошибка копирования:', err);
                alert('Не удалось скопировать код');
            });
        });
    });
}

function initQuizHandlers() {
    document.querySelectorAll('.reveal-btn').forEach(button => {
        button.addEventListener('click', function() {
            const answerBlock = this.closest('.quiz-question').querySelector('.question-answer');
            const isHidden = answerBlock.classList.contains('hidden');

            if (isHidden) {
                answerBlock.classList.remove('hidden');
                this.innerHTML = '<i class="icon-eye-slash"></i> Скрыть ответ';
            } else {
                answerBlock.classList.add('hidden');
                this.innerHTML = '<i class="icon-eye"></i> Показать ответ';
            }
        });
    });
}

// Глобальные функции для вызова из шаблона
window.toggleDarkMode = function() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));

    // Перерендер Mermaid с новой темой
    const theme = document.body.classList.contains('dark-mode') ? 'dark' : 'default';
    mermaid.initialize({ ...mermaid.mermaidAPI.getConfig(), theme });
    renderMermaidDiagrams();
};

window.scrollToTop = function() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

window.toggleAnswer = function(button) {
    const answerBlock = button.closest('.quiz-question').querySelector('.question-answer');
    const isHidden = answerBlock.classList.contains('hidden');

    if (isHidden) {
        answerBlock.classList.remove('hidden');
        button.innerHTML = '<i class="icon-eye-slash"></i> Скрыть ответ';
    } else {
        answerBlock.classList.add('hidden');
        button.innerHTML = '<i class="icon-eye"></i> Показать ответ';
    }
};

window.copyCode = function(button) {
    const codeBlock = button.closest('.code-container').querySelector('code');
    const code = codeBlock.textContent;

    navigator.clipboard.writeText(code).then(() => {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="icon-check"></i> Скопировано!';
        button.style.background = '#10b981';

        setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = '';
        }, 2000);
    }).catch(err => {
        console.error('Ошибка копирования:', err);
        alert('Не удалось скопировать код');
    });
};

window.toggleMermaidFullscreen = function(element) {
    const container = element || this;
    const diagram = container.querySelector('.mermaid-diagram');

    if (!diagram) return;

    const isFullscreen = diagram.classList.contains('mermaid-fullscreen');

    if (isFullscreen) {
        diagram.classList.remove('mermaid-fullscreen');
        document.body.style.overflow = 'auto';
    } else {
        diagram.classList.add('mermaid-fullscreen');
        document.body.style.overflow = 'hidden';
    }
};

window.exportMermaidDiagram = function(element) {
    const container = element.closest('.mermaid-container');
    const svg = container.querySelector('svg');

    if (!svg) {
        alert('Диаграмма не найдена');
        return;
    }

    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = function() {
        canvas.width = svg.width.baseVal.value;
        canvas.height = svg.height.baseVal.value;
        ctx.drawImage(img, 0, 0);

        const pngUrl = canvas.toDataURL('image/png');
        const downloadLink = document.createElement('a');
        downloadLink.download = 'mermaid-diagram.png';
        downloadLink.href = pngUrl;
        downloadLink.click();
    };

    img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
};

window.retryMermaid = function(button) {
    const errorDiv = button.closest('.mermaid-error');
    const diagram = errorDiv.closest('.mermaid-diagram');
    const mermaidCode = diagram.dataset.mermaid;

    try {
        mermaid.render(`mermaid-retry-${Date.now()}`, mermaidCode, (svgCode) => {
            diagram.innerHTML = svgCode;
        });
    } catch (error) {
        alert('Ошибка при повторной попытке рендера: ' + error.message);
    }
};

// Восстанавливаем тему при загрузке
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}

// Обработка нажатия Escape для выхода из полноэкранного режима
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const fullscreenDiagram = document.querySelector('.mermaid-diagram.mermaid-fullscreen');
        if (fullscreenDiagram) {
            fullscreenDiagram.classList.remove('mermaid-fullscreen');
            document.body.style.overflow = 'auto';
        }
    }
});

// Обработка печати
window.addEventListener('beforeprint', function() {
    document.querySelectorAll('.question-answer').forEach(answer => {
        answer.classList.remove('hidden');
    });

    document.querySelectorAll('.reveal-btn').forEach(btn => {
        btn.style.display = 'none';
    });
});

window.addEventListener('afterprint', function() {
    document.querySelectorAll('.reveal-btn').forEach(btn => {
        btn.style.display = 'flex';
    });
});
