let currentStep = 0;
const steps = document.querySelectorAll('.step');
const progress = document.getElementById('progress');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const uploadedFiles = []; // URL загруженных файлов
const collectedLinks = []; // Загруженные ссылки


// Показать шаг
function showStep(n) {
    steps[currentStep].classList.remove('active');
    currentStep = n;
    if (currentStep >= steps.length) {
        submitForm();
        return false;
    }
    steps[currentStep].classList.add('active');
    progress.style.width = ((currentStep + 1) / steps.length) * 100 + '%';

    prevBtn.style.display = currentStep === 0 ? 'none' : 'inline';
    nextBtn.innerText = currentStep === steps.length - 1 ? 'Отправить' : 'Далее';

    // Специфика для шагов
    if (currentStep === 1) { // Дисциплина
        const select = document.getElementById('discipline');
        const custom = document.getElementById('disciplineCustom');
        select.addEventListener('change', () => {
            custom.style.display = select.value === 'Другое' ? 'block' : 'none';
        });
    }
    if (currentStep === 2) { // Материалы
        document.getElementById('files').addEventListener('change', handleFileUpload);
    }
}

// Валидация шага
function validateStep() {
    let valid = true;
    const errorElems = document.querySelectorAll('.error');
    errorElems.forEach(el => el.innerText = '');

    if (currentStep === 0) { // Название
        const title = document.getElementById('title');
        if (title.value.length < 5) {
            document.getElementById('titleError').innerText = 'Название должно быть минимум 5 символов';
            valid = false;
        }
    } else if (currentStep === 1) { // Дисциплина
        const select = document.getElementById('discipline');
        const custom = document.getElementById('disciplineCustom');
        if (select.value === '' || (select.value === 'Другое' && custom.value === '')) {
            document.getElementById('disciplineError').innerText = 'Выберите или введите дисциплину';
            valid = false;
        }
    } else if (currentStep === 2) { // Материалы
        // Опционально, но если добавлены - проверить формат
        const links = document.querySelectorAll('.link-input');
        links.forEach(link => {
            if (link.value && !link.checkValidity()) {
                document.getElementById('linksError').innerText = 'Некорректная ссылка';
                valid = false;
            }
        });
        // Файлы: проверка на тип (в upload)
    } else if (currentStep === 3) { // Комментарий
        // Опционально, без валидации
    }
    return valid;
}

// Навигация
function nextPrev(n) {
    if (n === 1 && !validateStep()) return false;
    if (n === -1 && currentStep === 0) return false;

    // Собрать ссылки перед переходом (для шага 2)
    if (currentStep === 2 && n === 1) {
        collectedLinks.length = 0;
        document.querySelectorAll('.link-input').forEach(input => {
            if (input.value) collectedLinks.push(input.value);
        });
    }

    showStep(currentStep + n);
}

// Добавление поля для ссылки
function addLinkField() {
    const container = document.getElementById('linksContainer');
    const input = document.createElement('input');
    input.type = 'url';
    input.className = 'link-input';
    input.placeholder = 'https://example.com';
    input.required = true;
    container.appendChild(input);
}

// Загрузка файлов
async function handleFileUpload(e) {
    const files = e.target.files;
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    uploadedFiles.length = 0;

    // Получаем данные пользователя
    const tg = window.Telegram.WebApp;
    const user = tg.initDataUnsafe.user;
    const userId = user?.id;

    for (let file of files) {
        if (!['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'].includes(file.type)) {
            document.getElementById('filesError').innerText = 'Поддерживаются только PDF, DOCX, PPTX';
            return;
        }
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(
                '/api/v1/media/upload',
                { method: 'POST', body: formData, headers: { 'X-User-ID': userId } }
            );
            const data = await response.json();
            uploadedFiles.push({ name: file.name, fileId: data.id });
            const li = document.createElement('li');
            li.textContent = file.name + ' (загружен)';
            fileList.appendChild(li);
        } catch (error) {
            document.getElementById('filesError').innerText = 'Ошибка загрузки';
        }
    }
}

// Отправка данных
function submitForm() {
    const disciplineSelect = document.getElementById('discipline').value;
    const discipline = disciplineSelect === 'Другое' ? document.getElementById('disciplineCustom').value : disciplineSelect;

    const data = {
        title: document.getElementById('title').value,
        discipline: discipline,
        materials: {
            files: uploadedFiles,
            links: collectedLinks
        },
        comment: document.getElementById('comment').value || null
    };

    Telegram.WebApp.sendData(JSON.stringify(data));
    Telegram.WebApp.close();
}

// Инициализация
showStep(currentStep);
