const API_URL = 'http://127.0.0.1:8001';
let currentTasks = [];
let currentUsers = [];
let editingTaskId = null;
let editRowCounter = 1; // Добавлено

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM загружен');
    
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    loadTasks();
    loadUsers();
    setupEditForm();
});

// ========== ФУНКЦИИ ДЛЯ ПОСТОВ В МОДАЛЬНОМ ОКНЕ ==========
function addEditPostRow() {
    const container = document.getElementById('edit-posts-container');
    if (!container) return;
    
    const row = document.createElement('div');
    row.className = 'post-row';
    row.id = `edit-post-row-${editRowCounter}`;
    row.innerHTML = `
        <input type="url" class="edit-post-input" placeholder="https://vk.com/wall...">
        <button type="button" class="add-post-btn" onclick="addEditPostRow()">+</button>
        <button type="button" class="delete-post-btn" onclick="deleteEditPostRow('edit-post-row-${editRowCounter}')">×</button>
    `;
    container.appendChild(row);
    editRowCounter++;
}

function deleteEditPostRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        row.remove();
    }
}

// ========== УПРАВЛЕНИЕ ВКЛАДКАМИ ==========
function showMainTab(tabName) {
    console.log('Переключение на вкладку:', tabName);
    
    document.querySelectorAll('.main-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = Array.from(document.querySelectorAll('.main-tab')).find(
        btn => btn.textContent.trim().toLowerCase().includes(tabName)
    );
    if (activeBtn) activeBtn.classList.add('active');
    
    document.querySelectorAll('.tab-block').forEach(block => {
        block.style.display = 'none';
    });
    
    const targetBlock = document.getElementById(tabName + '-block');
    if (targetBlock) targetBlock.style.display = 'block';
}

function showTaskTab(tabName) {
    console.log('Переключение на подвкладку:', tabName);
    
    document.querySelectorAll('.task-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = Array.from(document.querySelectorAll('.task-tab')).find(
        btn => btn.textContent.trim().toLowerCase().includes(tabName)
    );
    if (activeBtn) activeBtn.classList.add('active');
    
    document.getElementById('active-tasks').style.display = 'none';
    document.getElementById('archive-tasks').style.display = 'none';
    
    const targetList = document.getElementById(tabName + '-tasks');
    if (targetList) targetList.style.display = 'block';
}

// ========== ЗАГРУЗКА ЗАДАНИЙ ==========
async function loadTasks() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/tasks`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) throw new Error('Ошибка загрузки');
        
        const data = await response.json();
        currentTasks = data.tasks || [];
        displayTasks();
    } catch (error) {
        console.error('Ошибка:', error);
        const activeList = document.getElementById('active-list');
        const archiveList = document.getElementById('archive-list');
        if (activeList) activeList.innerHTML = '<div class="task-card error">Ошибка загрузки</div>';
        if (archiveList) archiveList.innerHTML = '<div class="task-card error">Ошибка загрузки</div>';
    }
}

function displayTasks() {
    const now = new Date();
    
    const activeTasks = currentTasks.filter(task => {
        const taskDeadline = new Date(task.deadline);
        return task.is_active && taskDeadline > now;
    });
    
    const archiveTasks = currentTasks.filter(task => {
        const taskDeadline = new Date(task.deadline);
        return !task.is_active || taskDeadline <= now;
    });

    displayTaskList('active-list', activeTasks, true);
    displayTaskList('archive-list', archiveTasks, false);
}

function displayTaskList(elementId, tasks, isActive) {
    const container = document.getElementById(elementId);
    if (!container) return;
    
    if (tasks.length === 0) {
        container.innerHTML = '<div class="task-card empty">Нет заданий</div>';
        return;
    }

    container.innerHTML = tasks.map(task => {
        const description = task.description.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        
        return `
        <div class="task-card" data-task-id="${task.id}">
            <div class="task-header">
                <h3 class="task-title">${task.title}</h3>
                <span class="task-badge">${task.task_type === 'auto' ? 'Авто' : 'Ручная'}</span>
            </div>
            <div class="task-desc">${description}</div>
            <div class="task-meta">
                <span>Дедлайн: ${new Date(task.deadline).toLocaleString()}</span>
                ${task.auto_type ? `<span>Тип: ${task.auto_type === 'likes' ? 'Лайки' : 'Комментарии'}</span>` : ''}
                ${task.file_format ? `<span>Формат: ${task.file_format}</span>` : ''}
            </div>
            <div class="task-actions">
                ${isActive ? `
                    <button class="edit-btn" onclick="openEditModal(${task.id})">Редактировать</button>
                    <button class="delete-btn" onclick="moveToArchive(${task.id})">В архив</button>
                ` : `
                    <button class="restore-btn" onclick="restoreTask(${task.id})">Восстановить</button>
                    <button class="delete-btn" onclick="deleteTask(${task.id})">Удалить</button>
                `}
            </div>
        </div>
    `}).join('');
}

// ========== МОДАЛЬНОЕ ОКНО РЕДАКТИРОВАНИЯ ==========
function toggleEditFields() {
    const taskType = document.getElementById('edit-task-type').value;
    const autoSettings = document.getElementById('edit-auto-settings');
    const formatBlock = document.getElementById('edit-format-block');
    const postsBlock = document.getElementById('edit-posts-block');
    
    if (autoSettings) autoSettings.style.display = taskType === 'auto' ? 'block' : 'none';
    if (formatBlock) formatBlock.style.display = taskType === 'manual' ? 'block' : 'none';
    if (postsBlock) postsBlock.style.display = taskType === 'auto' ? 'block' : 'none';
}

function setupEditForm() {
    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!editingTaskId) {
                closeEditModal();
                return;
            }

            const taskType = document.getElementById('edit-task-type').value;
            
            // Собираем посты
            const postInputs = document.querySelectorAll('#edit-posts-container .edit-post-input');
            const posts = [];
            postInputs.forEach(input => {
                if (input.value.trim()) {
                    posts.push(input.value.trim());
                }
            });
            
            const taskData = {
                title: document.getElementById('edit-title').value,
                description: document.getElementById('edit-description').value,
                task_type: taskType,
                auto_type: taskType === 'auto' ? document.getElementById('edit-auto-type').value : null,
                file_format: taskType === 'manual' ? document.getElementById('edit-file-format').value : null,
                posts: posts,
                deadline: new Date(document.getElementById('edit-deadline').value).toISOString(),
                is_active: true
            };

            try {
                const token = localStorage.getItem('token');
                const response = await fetch(`${API_URL}/api/tasks/${editingTaskId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(taskData)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка обновления');
                }

                closeEditModal();
                loadTasks();
                alert('Задание успешно обновлено');
            } catch (error) {
                console.error('Ошибка:', error);
                alert('Ошибка: ' + error.message);
            }
        });
    }
}

function openEditModal(taskId) {
    console.log('Открытие редактирования для задания:', taskId);
    
    const task = currentTasks.find(t => t.id === taskId);
    if (!task) {
        console.error('Задание не найдено:', taskId);
        return;
    }
    
    editingTaskId = taskId;
    editRowCounter = 1; // Сбрасываем счетчик
    
    const elements = {
        id: document.getElementById('edit-id'),
        title: document.getElementById('edit-title'),
        description: document.getElementById('edit-description'),
        taskType: document.getElementById('edit-task-type'),
        autoType: document.getElementById('edit-auto-type'),
        fileFormat: document.getElementById('edit-file-format'),
        deadline: document.getElementById('edit-deadline')
    };
    
    for (const [key, el] of Object.entries(elements)) {
        if (!el) {
            console.error(`Элемент не найден: edit-${key}`);
            alert('Ошибка: не найдены элементы формы');
            return;
        }
    }
    
    // Заполняем основные поля
    elements.id.value = task.id;
    elements.title.value = task.title;
    elements.description.value = task.description;
    elements.taskType.value = task.task_type;
    
    if (task.auto_type) {
        elements.autoType.value = task.auto_type;
    }
    
    if (task.file_format) {
        elements.fileFormat.value = task.file_format;
    }
    
    // Заполняем посты
    const postsContainer = document.getElementById('edit-posts-container');
    if (postsContainer) {
        postsContainer.innerHTML = '';
        
        const posts = task.posts || [];
        
        if (posts.length === 0) {
            const row = document.createElement('div');
            row.className = 'post-row';
            row.id = 'edit-post-row-0';
            row.innerHTML = `
                <input type="url" class="edit-post-input" placeholder="https://vk.com/wall...">
                <button type="button" class="add-post-btn" onclick="addEditPostRow()">+</button>
            `;
            postsContainer.appendChild(row);
        } else {
            posts.forEach((post, index) => {
                const row = document.createElement('div');
                row.className = 'post-row';
                row.id = `edit-post-row-${index}`;
                row.innerHTML = `
                    <input type="url" class="edit-post-input" value="${post.replace(/"/g, '&quot;')}" placeholder="https://vk.com/wall...">
                    <button type="button" class="add-post-btn" onclick="addEditPostRow()">+</button>
                    <button type="button" class="delete-post-btn" onclick="deleteEditPostRow('edit-post-row-${index}')">×</button>
                `;
                postsContainer.appendChild(row);
            });
            editRowCounter = posts.length;
        }
    }
    
    // Форматируем дату
    const deadline = new Date(task.deadline);
    const year = deadline.getFullYear();
    const month = String(deadline.getMonth() + 1).padStart(2, '0');
    const day = String(deadline.getDate()).padStart(2, '0');
    const hours = String(deadline.getHours()).padStart(2, '0');
    const minutes = String(deadline.getMinutes()).padStart(2, '0');
    elements.deadline.value = `${year}-${month}-${day}T${hours}:${minutes}`;
    
    toggleEditFields();
    
    const modal = document.getElementById('editModal');
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    modal.style.display = 'none';
    editingTaskId = null;
    document.body.style.overflow = 'auto';
}

// ========== ДЕЙСТВИЯ С ЗАДАНИЯМИ ==========
async function moveToArchive(taskId) {
    console.log('Перемещение в архив:', taskId);
    
    if (!confirm('Переместить задание в архив?')) return;
    
    const task = currentTasks.find(t => t.id === taskId);
    if (!task) return;
    
    try {
        const token = localStorage.getItem('token');
        
        const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                title: task.title,
                description: task.description,
                task_type: task.task_type,
                auto_type: task.auto_type,
                file_format: task.file_format,
                posts: task.posts || [],
                deadline: task.deadline,
                is_active: false
            })
        });
        
        if (response.ok) {
            alert('Задание перемещено в архив');
            loadTasks();
        } else {
            const error = await response.json();
            alert('Ошибка: ' + (error.detail || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при перемещении в архив: ' + error.message);
        loadTasks();
    }
}

async function restoreTask(taskId) {
    console.log('Восстановление задания:', taskId);
    
    if (!confirm('Восстановить задание из архива?')) return;
    
    const task = currentTasks.find(t => t.id === taskId);
    if (!task) return;
    
    try {
        const token = localStorage.getItem('token');
        
        const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                title: task.title,
                description: task.description,
                task_type: task.task_type,
                auto_type: task.auto_type,
                file_format: task.file_format,
                posts: task.posts || [],
                deadline: task.deadline,
                is_active: true
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка восстановления');
        }
        
        alert('Задание восстановлено из архива');
        loadTasks();
        
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при восстановлении: ' + error.message);
        loadTasks();
    }
}

async function deleteTask(taskId) {
    console.log('Удаление задания:', taskId);
    
    if (!confirm('Вы уверены, что хотите удалить задание навсегда? Это действие нельзя отменить.')) return;
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка удаления');
        }
        
        alert('Задание удалено навсегда');
        loadTasks();
        
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при удалении: ' + error.message);
    }
}

// ========== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ ==========
async function loadUsers() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/bot-users`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            currentUsers = await response.json();
        } else {
            currentUsers = [
                {id:1, vk_id:123456, name:"Иванов Иван Иванович", institute:"ИКНК", group_num:"3530901/80101", is_active:true, completed_tasks:3},
                {id:2, vk_id:234567, name:"Петрова Анна Сергеевна", institute:"ИПМЭИТ", group_num:"3734303/30101", is_active:true, completed_tasks:5},
                {id:3, vk_id:345678, name:"Сидоров Петр Алексеевич", institute:"ГИ", group_num:"3930102/20201", is_active:false, completed_tasks:1}
            ];
        }
        displayUsers();
        updateStats();
    } catch (error) {
        console.error('Ошибка загрузки пользователей:', error);
    }
}

function displayUsers() {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;

    if (currentUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">Нет пользователей</td> </tr>';
        return;
    }

    tbody.innerHTML = currentUsers.map(user => `
         <tr>
            <td style="padding: 12px;">${user.vk_id}</td>
            <td style="padding: 12px;">${user.name}</td>
            <td style="padding: 12px;">${user.institute || '-'}</td>
            <td style="padding: 12px;">${user.group_num || '-'}</td>
            <td style="padding: 12px;"><span class="status ${user.is_active ? 'active' : 'inactive'}">${user.is_active ? 'Активен' : 'Неактивен'}</span></td>
            <td style="padding: 12px;">${user.completed_tasks || 0}</td>
         </tr>
    `).join('');
}

function updateStats() {
    const total = document.getElementById('total-users');
    const active = document.getElementById('active-users');
    const completed = document.getElementById('total-completed');
    
    if (total) total.textContent = currentUsers.length;
    if (active) active.textContent = currentUsers.filter(u => u.is_active).length;
    if (completed) completed.textContent = currentUsers.reduce((sum, u) => sum + (u.completed_tasks || 0), 0);
}

function searchUsers() {
    const search = document.getElementById('userSearch').value.toLowerCase().trim();
    if (!search) {
        displayUsers();
        return;
    }
    
    const filtered = currentUsers.filter(u => 
        u.name.toLowerCase().includes(search) ||
        (u.institute && u.institute.toLowerCase().includes(search)) ||
        (u.group_num && u.group_num.toLowerCase().includes(search))
    );
    
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">Ничего не найдено</td></tr>';
        return;
    }
    
    tbody.innerHTML = filtered.map(user => `
         <tr>
            <td style="padding: 12px;">${user.vk_id}</td>
            <td style="padding: 12px;">${user.name}</td>
            <td style="padding: 12px;">${user.institute || '-'}</td>
            <td style="padding: 12px;">${user.group_num || '-'}</td>
            <td style="padding: 12px;"><span class="status ${user.is_active ? 'active' : 'inactive'}">${user.is_active ? 'Активен' : 'Неактивен'}</span></td>
            <td style="padding: 12px;">${user.completed_tasks || 0}</td>
         </tr>
    `).join('');
}

function resetSearch() {
    document.getElementById('userSearch').value = '';
    displayUsers();
}

window.onclick = function(event) {
    const modal = document.getElementById('editModal');
    if (event.target === modal) {
        closeEditModal();
    }
}