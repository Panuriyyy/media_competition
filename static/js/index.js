document.addEventListener('DOMContentLoaded', function() {
    // Проверка авторизации
    if (!localStorage.getItem('token')) {
        window.location.href = 'login.html';
        return;
    }

    const manualRadio = document.getElementById('manual_main');
    const autoRadio = document.getElementById('auto_main');
    const formatBlock = document.getElementById('format_block');
    const autoSettings = document.getElementById('auto_settings');
    const postsBlock = document.getElementById('posts_block');
    const taskForm = document.getElementById('taskForm');
    const postsContainer = document.getElementById('posts_container');

    // Изначально скрываем все блоки
    if (autoSettings) autoSettings.style.display = 'none';
    if (formatBlock) formatBlock.style.display = 'none';
    if (postsBlock) postsBlock.style.display = 'none';

    // Счетчик для уникальных ID строк
    let rowCounter = 1;

    // Функция для добавления нового поля поста
    window.addPostRow = function() {
        const rowId = `post-row-${rowCounter}`;
        const row = document.createElement('div');
        row.className = 'post-row';
        row.id = rowId;
        row.innerHTML = `
            <input type="url" class="post-input" placeholder="https://vk.com/wall...">
            <button type="button" class="add-post-btn" onclick="addPostRow()">+</button>
            <button type="button" class="delete-post-btn" onclick="deletePostRow('${rowId}')">×</button>
        `;
        postsContainer.appendChild(row);
        rowCounter++;
    };

    // Функция для удаления строки с постом
    window.deletePostRow = function(rowId) {
        const row = document.getElementById(rowId);
        if (row) {
            row.remove();
        }
    };

    if (manualRadio) {
        manualRadio.addEventListener('change', function() {
            if (this.checked) {
                if (formatBlock) formatBlock.style.display = 'block';
                if (autoSettings) autoSettings.style.display = 'none';
                if (postsBlock) postsBlock.style.display = 'none';
            }
        });
    }

    if (autoRadio) {
        autoRadio.addEventListener('change', function() {
            if (this.checked) {
                if (formatBlock) formatBlock.style.display = 'none';
                if (autoSettings) autoSettings.style.display = 'block';
                if (postsBlock) postsBlock.style.display = 'block';
            }
        });
    }

    // Обработка отправки формы
    if (taskForm) {
        taskForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            try {
                const token = localStorage.getItem('token');
                if (!token) {
                    window.location.href = 'login.html';
                    return;
                }

                // Собираем данные формы
                const formData = {
                    title: `Задание ${Date.now()}`,
                    description: document.querySelector('textarea[name="description"]')?.value || '',
                    task_type: document.querySelector('input[name="check_type"]:checked')?.value,
                    auto_type: document.querySelector('input[name="auto_type"]:checked')?.value,
                    file_format: document.querySelector('select[name="format"]')?.value,
                    deadline: document.querySelector('input[name="dd"]')?.value
                };

                // Добавляем посты, если это автоматическое задание
                if (formData.task_type === 'auto') {
                    const postInputs = document.querySelectorAll('.post-input');
                    const posts = [];
                    postInputs.forEach(input => {
                        if (input.value.trim()) {
                            posts.push(input.value.trim());
                        }
                    });
                    formData.posts = posts;
                }

                console.log('Отправка данных:', formData);

                // Валидация
                if (!formData.task_type) {
                    alert('Выберите тип задания');
                    return;
                }

                if (!formData.description) {
                    alert('Введите описание задания');
                    return;
                }

                if (!formData.deadline) {
                    alert('Выберите дедлайн');
                    return;
                }

                // Преобразуем дату
                formData.deadline = new Date(formData.deadline).toISOString();

                // Отправляем запрос
                const response = await fetch('http://127.0.0.1:8001/api/tasks', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(formData)
                });

                const responseText = await response.text();
                console.log('Ответ сервера:', responseText);

                if (!response.ok) {
                    try {
                        const errorData = JSON.parse(responseText);
                        throw new Error(errorData.detail || `Ошибка ${response.status}`);
                    } catch {
                        throw new Error(responseText || `Ошибка ${response.status}`);
                    }
                }

                const data = JSON.parse(responseText);
                alert('✅ Задание успешно создано!');
                
                // Очищаем форму
                taskForm.reset();
                if (autoSettings) autoSettings.style.display = 'none';
                if (formatBlock) formatBlock.style.display = 'none';
                if (postsBlock) postsBlock.style.display = 'none';
                
                // Сбрасываем посты до одного пустого поля
                postsContainer.innerHTML = `
                    <div class="post-row" id="post-row-0">
                        <input type="url" class="post-input" placeholder="https://vk.com/wall...">
                        <button type="button" class="add-post-btn" onclick="addPostRow()">+</button>
                    </div>
                `;
                rowCounter = 1;
                
                // Перенаправляем в админку
                setTimeout(() => {
                    window.location.href = 'admin.html';
                }, 2000);

            } catch (error) {
                console.error('Ошибка:', error);
                alert(`❌ Ошибка: ${error.message}`);
            }
        });
    }
});