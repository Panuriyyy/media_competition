const API_URL = 'http://127.0.0.1:8001';
let currentTasks = [];
let currentTaskId = null;
let currentTaskType = null;
let notificationsOpen = false;

document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('token')) return window.location.href = 'login.html';
    
    loadUserInfo();
    loadAvailableTasks();
    loadHistory();
    loadNotifications();
    
    // ПУНКТ 3: Поллинг уведомлений каждые 30 секунд
    setInterval(loadNotifications, 30000);
});

// ПУНКТ 6: Функция склонения слова "баллы"
function declOfNum(n, text_forms) {
    n = Math.abs(n) % 100;
    const n1 = n % 10;
    if (n > 10 && n < 20) return text_forms[2];
    if (n1 > 1 && n1 < 5) return text_forms[1];
    if (n1 === 1) return text_forms[0];
    return text_forms[2];
}

function escapeHtml(str) {
    return str ? str.replace(/[&<>]/g, m => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[m])) : '';
}

function switchUserTab(tab) {
    document.querySelectorAll('.main-tab').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('active-tasks-block').style.display = tab === 'active' ? 'block' : 'none';
    document.getElementById('history-tasks-block').style.display = tab === 'history' ? 'block' : 'none';
    tab === 'active' ? loadAvailableTasks() : loadHistory();
}

// ========== ПРОФИЛЬ И УВЕДОМЛЕНИЯ ==========

async function loadUserInfo() {
    try {
        const res = await fetch(`${API_URL}/api/users/me`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        if (res.ok) document.getElementById('user-name').textContent = (await res.json()).full_name;
    } catch (e) { console.error('Ошибка загрузки профиля:', e); }
}

function toggleNotifications() {
    const panel = document.querySelector('.notifications-panel');
    notificationsOpen = !notificationsOpen;
    if (panel) panel.style.display = notificationsOpen ? 'block' : 'none';
}

async function loadNotifications() {
    try {
        const res = await fetch(`${API_URL}/api/users/me/notifications`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        if (res.ok) renderNotifications(await res.json());
    } catch (e) {}
}

function renderNotifications(notifications) {
    const list = document.querySelector('.notifications-list');
    const badge = document.querySelector('.notif-badge');
    if (!list) return;
    
    if (badge) badge.style.display = notifications.some(n => !n.is_read) ? 'block' : 'none';
    
    if (!notifications.length) {
        list.innerHTML = '<div style="padding:15px; text-align:center; opacity:0.5;">Уведомлений нет</div>';
        return;
    }
    
    list.innerHTML = notifications.map(n => `
        <div class="notification-item ${n.is_read ? '' : 'unread'}" onclick="markAsRead(${n.id})" style="border-left: ${n.is_read ? 'none' : '3px solid #4CAF50'}; padding: 10px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <div class="notif-title" style="font-weight: bold; margin-bottom: 5px;">${escapeHtml(n.title)}</div>
            <div class="notif-message" style="font-size: 0.9em; opacity: 0.8;">${escapeHtml(n.message)}</div>
        </div>
    `).join('');
}

async function markAsRead(id) {
    await fetch(`${API_URL}/api/notifications/${id}/read`, { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
    loadNotifications();
}

// ========== ЗАДАНИЯ И ИСТОРИЯ ==========

async function loadAvailableTasks() {
    const container = document.getElementById('tasks-list');
    container.innerHTML = '<p>Загрузка...</p>';
    try {
        const res = await fetch(`${API_URL}/api/tasks/available`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        const tasks = await res.json();
        currentTasks = tasks;
        if (!tasks.length) return container.innerHTML = '<p>Активных заданий нет.</p>';
        
        container.innerHTML = tasks.map(t => {
            // Применяем склонение баллов
            const pointsText = declOfNum(t.points_at_stake, ['балл', 'балла', 'баллов']);
            return `
            <div class="task-card">
                <h3>${escapeHtml(t.title)}</h3>
                <p>${escapeHtml(t.description).substring(0, 100)}...</p>
                <div class="task-footer">
                    <span class="points" style="color: #FFD700;">★ ${t.points_at_stake} ${pointsText}</span>
                    <button onclick="openTaskModal(${t.id})" class="btn-primary">Выполнить</button>
                </div>
            </div>`;
        }).join('');
    } catch (e) { container.innerHTML = '<p>Ошибка загрузки заданий.</p>'; }
}

async function loadHistory() {
    const tbody = document.getElementById('history-table-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Загрузка...</td></tr>';
    try {
        const res = await fetch(`${API_URL}/api/users/me/history`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        const history = await res.json();
        if (!history.length) return tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Вы еще не сдавали работы</td></tr>';
        
        tbody.innerHTML = history.map(h => {
            const statusMap = { 'pending': 'Проверка', 'approved': 'Принято', 'rejected': 'Отклонено' };
            const color = h.status === 'approved' ? '#4CAF50' : (h.status === 'rejected' ? '#f44336' : '#ff9800');
            return `
                <tr>
                    <td>Задание #${h.task_id}</td>
                    <td style="color:${color}; font-weight: bold;">${statusMap[h.status]}</td>
                    <td><strong>${h.score}</strong></td>
                    <td style="opacity:0.6">${new Date(h.submitted_at || Date.now()).toLocaleDateString()}</td>
                </tr>`;
        }).join('');
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Ошибка загрузки истории</td></tr>'; }
}

// ========== МОДАЛКА И ОТПРАВКА ==========

function openTaskModal(taskId) {
    const task = currentTasks.find(t => t.id === taskId);
    if (!task) return;

    currentTaskId = task.id;
    currentTaskType = task.task_type;
    
    document.getElementById('modal-task-title').textContent = task.title;
    document.getElementById('modal-task-desc').innerHTML = escapeHtml(task.description).replace(/\n/g, '<br>');

    const fileInput = document.getElementById('submission-file');
    const urlInput = document.getElementById('submission-url');
    const fileBlock = document.getElementById('modal-file-input');
    const postsBlock = document.getElementById('modal-posts');

    if (fileInput) fileInput.value = '';
    if (urlInput) urlInput.value = '';

    if (task.task_type === 'auto') {
        if (fileBlock) fileBlock.style.display = 'none';
        if (postsBlock) {
            postsBlock.style.display = 'block';
            let urls = [];
            try { if(task.posts_urls) urls = JSON.parse(task.posts_urls); } catch(e){}
            postsBlock.innerHTML = '<strong>Ссылки для выполнения:</strong><ul style="margin-top:10px;">' + urls.map(u => `<li><a href="${u}" target="_blank" style="color:#4CAF50; text-decoration:none;">${u}</a></li>`).join('') + '</ul>';
        }
    } else {
        if (postsBlock) postsBlock.style.display = 'none';
        if (fileBlock) fileBlock.style.display = 'block';
        
        const desc = task.description.toUpperCase();
        
        // ПУНКТ 5: Точная валидация и скрытие ненужных полей
        if (desc.includes("PNG / JPG")) {
            if (fileInput) { fileInput.style.display = 'block'; fileInput.setAttribute('accept', '.jpg,.jpeg,.png'); }
            if (urlInput) urlInput.style.display = 'none';
        } 
        else if (desc.includes("DOC / DOCX / PDF")) {
            if (fileInput) { fileInput.style.display = 'block'; fileInput.setAttribute('accept', '.pdf,.doc,.docx'); }
            if (urlInput) urlInput.style.display = 'none';
        } 
        else if (desc.includes("СКА НА ВИДЕО") || desc.includes("ВИДЕО")) {
            if (fileInput) fileInput.style.display = 'none';
            if (urlInput) { urlInput.style.display = 'block'; urlInput.placeholder = "Вставьте ссылку на видео"; }
        } 
        else {
            if (fileInput) { fileInput.style.display = 'block'; fileInput.removeAttribute('accept'); }
            if (urlInput) { urlInput.style.display = 'block'; urlInput.placeholder = "Ссылка (если нужна)"; }
        }
    }
    
    const modal = document.getElementById('taskModal');
    if (modal) modal.style.display = 'flex';
}

function closeTaskModal() {
    const modal = document.getElementById('taskModal');
    if (modal) modal.style.display = 'none';
    currentTaskId = null;
}

async function submitTask() {
    if (!currentTaskId) return;
    const formData = new FormData();
    
    if (currentTaskType === 'manual') {
        const fileInput = document.getElementById('submission-file');
        const urlInput = document.getElementById('submission-url');
        
        let hasData = false;
        
        // Собираем данные только с тех инпутов, которые не скрыты
        if (fileInput && fileInput.style.display !== 'none' && fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0]);
            hasData = true;
        }
        if (urlInput && urlInput.style.display !== 'none' && urlInput.value.trim()) {
            formData.append('submission_url', urlInput.value.trim());
            hasData = true;
        }
        
        if (!hasData) return alert('Пожалуйста, прикрепите файл или вставьте ссылку, как указано в задании.');
    } else {
        // Заглушка для автопроверки
        formData.append('submission_url', 'auto_check_vk');
    }

    try {
        const res = await fetch(`${API_URL}/api/tasks/${currentTaskId}/submit`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
            body: formData
        });

        if (res.ok) {
            alert('Работа успешно отправлена!');
            closeTaskModal();
            loadAvailableTasks();
            loadHistory();
            switchUserTab('history');
        } else {
            const err = await res.json();
            alert(`Ошибка: ${err.detail}`);
        }
    } catch (e) { alert('Ошибка соединения с сервером.'); }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = 'login.html';
}