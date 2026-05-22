const API_URL = 'http://127.0.0.1:8001';
let currentTasks = [];
let currentTaskId = null;
let currentTaskType = null;

document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('token')) return window.location.href = 'login.html';

    loadUserInfo();
    loadAvailableTasks();
    loadHistory();
    loadNotifications();
    startUnreadPolling();

    const notifIcon = document.getElementById('notifications-icon');
    if (notifIcon) notifIcon.addEventListener('click', toggleNotifications);

    const markAllBtn = document.getElementById('mark-all-read');
    if (markAllBtn) markAllBtn.addEventListener('click', markAllNotificationsRead);
});

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

const TAB_BLOCKS = {
    active: 'active-tasks-block',
    history: 'history-tasks-block',
    rating: 'rating-tasks-block',
    about: 'about-tasks-block',
};

function switchUserTab(tab) {
    document.querySelectorAll('.main-tab').forEach(btn => btn.classList.remove('active'));
    const activeBtn = Array.from(document.querySelectorAll('.main-tab')).find(btn =>
        btn.getAttribute('onclick')?.includes(`'${tab}'`)
    );
    if (activeBtn) activeBtn.classList.add('active');

    Object.values(TAB_BLOCKS).forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    const block = document.getElementById(TAB_BLOCKS[tab]);
    if (block) block.style.display = 'block';

    if (tab === 'active') loadAvailableTasks();
    if (tab === 'history') loadHistory();
    if (tab === 'rating') loadRatingUser();
    if (tab === 'about') loadAboutUser();
}

// ========== ПРОФИЛЬ ==========

async function loadUserInfo() {
    try {
        const res = await fetch(`${API_URL}/api/users/me`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) document.getElementById('user-name').textContent = (await res.json()).full_name;
    } catch (e) { console.error('Ошибка загрузки профиля:', e); }
}

// ========== УВЕДОМЛЕНИЯ ==========

function toggleNotifications() {
    const panel = document.getElementById('notifications-panel');
    const isOpen = panel.style.display === 'block';
    panel.style.display = isOpen ? 'none' : 'block';
    if (!isOpen) loadNotifications();
}

async function loadNotifications() {
    try {
        const res = await fetch(`${API_URL}/api/users/me/notifications`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) renderNotifications(await res.json());
    } catch (e) {}
}

function renderNotifications(notifications) {
    const list = document.getElementById('notifications-list');
    const badge = document.getElementById('notif-badge');
    if (!list) return;

    if (badge) {
        const unreadCount = notifications.filter(n => !n.is_read).length;
        badge.style.display = unreadCount > 0 ? 'block' : 'none';
    }

    if (!notifications.length) {
        list.innerHTML = '<div style="padding:15px; text-align:center; opacity:0.5;">Уведомлений нет</div>';
        return;
    }

    list.innerHTML = notifications.map(n => `
        <div class="notification-item ${n.is_read ? '' : 'unread'}" onclick="markAsRead(${n.id})">
            <div class="notif-title">${escapeHtml(n.title)}</div>
            <div class="notif-message">${escapeHtml(n.message)}</div>
            <div class="notif-date">${formatDate(n.created_at)}</div>
        </div>
    `).join('');
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    if (diff < 60000) return 'только что';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} мин назад`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} ч назад`;
    return date.toLocaleDateString();
}

async function markAsRead(id) {
    await fetch(`${API_URL}/api/notifications/${id}/read`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    loadNotifications();
    updateUnreadBadge();
}

async function markAllNotificationsRead() {
    await fetch(`${API_URL}/api/notifications/mark-all-read`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    loadNotifications();
}

function startUnreadPolling() {
    if (window.unreadInterval) clearInterval(window.unreadInterval);
    window.unreadInterval = setInterval(updateUnreadBadge, 30000);
    updateUnreadBadge();
}

async function updateUnreadBadge() {
    try {
        const res = await fetch(`${API_URL}/api/users/me/notifications/unread-count`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById('notif-badge');
            if (badge) {
                if (data.unread_count > 0) {
                    badge.style.display = 'block';
                } else {
                    badge.style.display = 'none';
                }
            }
        }
    } catch (e) {}
}

function logout() {
    if (window.unreadInterval) clearInterval(window.unreadInterval);
    localStorage.removeItem('token');
    window.location.href = 'login.html';
}

// ========== ЗАДАНИЯ ==========

async function loadAvailableTasks() {
    const container = document.getElementById('tasks-list');
    container.innerHTML = '<p>Загрузка...</p>';
    try {
        const res = await fetch(`${API_URL}/api/tasks/available`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const tasks = await res.json();
        currentTasks = tasks;
        if (!tasks.length) return container.innerHTML = '<p>Активных заданий нет.</p>';

        container.innerHTML = tasks.map(t => {
            const pointsText = declOfNum(t.points_at_stake, ['балл', 'балла', 'баллов']);
            return `
            <div class="task-card">
                <h3>${escapeHtml(t.title)}</h3>
                <p>${t.description.length > 100 ? escapeHtml(t.description).substring(0, 100) + '...' : escapeHtml(t.description)}</p>
                <div class="task-footer">
                    <span style="color: #FFD700;">★ ${t.points_at_stake} ${pointsText}</span>
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
        const res = await fetch(`${API_URL}/api/users/me/history`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const history = await res.json();
        if (!history.length) return tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Вы еще не сдавали работы</td></tr>';

        tbody.innerHTML = history.map(h => {
            const statusMap = { 'pending': 'На проверке', 'approved': 'Принято', 'rejected': 'Отклонено' };
            const color = h.status === 'approved' ? '#4CAF50' : (h.status === 'rejected' ? '#f44336' : '#ff9800');
            return `
                <tr>
                    <td>${escapeHtml(h.task_title || `Задание #${h.task_id}`)}</td>
                    <td style="color:${color}; font-weight: bold;">${statusMap[h.status] || h.status}</td>
                    <td><strong>${h.score}</strong></td>
                    <td style="opacity:0.6">${new Date(h.submitted_at || Date.now()).toLocaleDateString()}</td>
                </tr>`;
        }).join('');
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Ошибка загрузки истории</td></tr>'; }
}

// ========== МОДАЛЬНОЕ ОКНО ЗАДАНИЯ ==========

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
            // posts_urls уже массив (сервер возвращает JSON-массив)
            const urls = Array.isArray(task.posts_urls) ? task.posts_urls : [];
            postsBlock.innerHTML = '<strong>Ссылки для выполнения:</strong><ul style="margin-top:10px;">' +
                urls.map(u => `<li><a href="${escapeHtml(u)}" target="_blank" style="color:#4CAF50; text-decoration:none;">${escapeHtml(u)}</a></li>`).join('') +
                '</ul>';
        }
    } else {
        if (postsBlock) postsBlock.style.display = 'none';
        if (fileBlock) fileBlock.style.display = 'block';

        const desc = task.description.toUpperCase();
        const toggle = document.getElementById('submission-toggle');

        if (desc.includes('ВИДЕО')) {
            // Только ссылка — скрыть переключатель, показать URL
            if (toggle) toggle.style.display = 'none';
            if (fileInput) fileInput.parentElement.style.display = 'none';
            const urlBlock = document.getElementById('url-input-block');
            if (urlBlock) urlBlock.style.display = 'block';
            if (urlInput) urlInput.placeholder = 'Вставьте ссылку на видео';
        } else {
            // Файл или ссылка — показать переключатель
            if (toggle) toggle.style.display = 'flex';
            if (desc.includes('JPG') || desc.includes('PNG') || desc.includes('ИЗОБРАЖ')) {
                if (fileInput) fileInput.setAttribute('accept', '.jpg,.jpeg,.png');
            } else if (desc.includes('PDF') || desc.includes('DOC')) {
                if (fileInput) fileInput.setAttribute('accept', '.pdf,.doc,.docx');
            } else {
                if (fileInput) fileInput.removeAttribute('accept');
            }
            setSubmissionType('file');
        }
    }

    const modal = document.getElementById('taskModal');
    if (modal) modal.style.display = 'flex';
}

function setSubmissionType(type) {
    const fileBlock = document.getElementById('file-upload-block');
    const urlBlock = document.getElementById('url-input-block');
    const lblFile = document.getElementById('lbl-file');
    const lblUrl = document.getElementById('lbl-url');
    if (fileBlock) fileBlock.style.display = type === 'file' ? 'block' : 'none';
    if (urlBlock) urlBlock.style.display = type === 'url' ? 'block' : 'none';
    if (lblFile) lblFile.classList.toggle('active-type', type === 'file');
    if (lblUrl) lblUrl.classList.toggle('active-type', type === 'url');
}

function closeTaskModal() {
    const modal = document.getElementById('taskModal');
    if (modal) modal.style.display = 'none';
    currentTaskId = null;
}

// ========== РЕЙТИНГ ==========

async function loadRatingUser() {
    const tbody = document.getElementById('rating-table-body-user');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Загрузка...</td></tr>';
    try {
        const res = await fetch(`${API_URL}/api/rating`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('user-rank-place').textContent = data.user_rank || '—';
        document.getElementById('user-rank-score').textContent = data.user_score || 0;

        if (!data.ratings.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Нет данных</td></tr>';
            return;
        }
        tbody.innerHTML = data.ratings.map((r, i) => `
            <tr style="${data.user_rank === i + 1 ? 'background:rgba(76,175,80,0.2);' : ''}">
                <td style="padding:10px; font-weight:${data.user_rank === i + 1 ? 'bold' : 'normal'};">${i + 1}</td>
                <td style="padding:10px;">${escapeHtml(r.full_name)}</td>
                <td style="padding:10px; opacity:0.7;">${escapeHtml(r.institute)}</td>
                <td style="padding:10px; font-weight:bold;">${r.total_score}</td>
            </tr>`
        ).join('');
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Ошибка загрузки</td></tr>'; }
}

// ========== О КОНКУРСЕ ==========

async function loadAboutUser() {
    try {
        const res = await fetch(`${API_URL}/api/about`);
        if (!res.ok) return;
        const data = await res.json();

        const content = document.getElementById('about-content-user');
        if (content) content.textContent = data.content || '(Информация о конкурсе пока не добавлена)';

        const newsList = document.getElementById('news-list-user');
        if (!newsList) return;
        if (!data.news.length) {
            newsList.innerHTML = '<p style="opacity:0.6;">Новостей пока нет</p>';
            return;
        }
        newsList.innerHTML = data.news.map(n => `
            <div style="background:rgba(255,255,255,0.07); border-radius:8px; padding:15px; margin-bottom:12px;">
                <strong style="color:white;">${escapeHtml(n.title)}</strong>
                <p style="margin-top:8px; opacity:0.85; white-space:pre-wrap;">${escapeHtml(n.content)}</p>
                <small style="opacity:0.5;">${new Date(n.created_at).toLocaleDateString()}</small>
            </div>`
        ).join('');
    } catch (e) { console.error(e); }
}

// ========== FAQ ==========

let faqPanelOpen = false;

function toggleFaqPanel() {
    const panel = document.getElementById('faq-panel');
    if (!panel) return;
    faqPanelOpen = !faqPanelOpen;
    panel.style.display = faqPanelOpen ? 'flex' : 'none';
    if (faqPanelOpen) loadFaqUser();
}

async function loadFaqUser() {
    const list = document.getElementById('faq-list');
    if (!list) return;
    list.innerHTML = '<p style="opacity:0.6; text-align:center;">Загрузка...</p>';
    try {
        const res = await fetch(`${API_URL}/api/faq`);
        if (!res.ok) return;
        const items = await res.json();
        if (!items.length) {
            list.innerHTML = '<p style="opacity:0.6; text-align:center;">Вопросы ещё не добавлены</p>';
            return;
        }
        list.innerHTML = items.map(f => `
            <div style="margin-bottom:14px;">
                <div onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'"
                    style="cursor:pointer; font-weight:600; color:white; padding:10px 12px; background:rgba(255,255,255,0.1); border-radius:8px; user-select:none;">
                    ${escapeHtml(f.question)}
                </div>
                <div style="display:none; padding:10px 12px; background:rgba(255,255,255,0.05); border-radius:0 0 8px 8px; color:rgba(255,255,255,0.85); font-size:0.95em; line-height:1.5; word-break:break-word;">
                    ${escapeHtml(f.answer).replace(/\n/g, '<br>')}
                </div>
            </div>`
        ).join('');
    } catch (e) { list.innerHTML = '<p style="color:#f44336;">Ошибка загрузки</p>'; }
}

// ========== МОДАЛЬНОЕ ОКНО ЗАДАНИЯ ==========

async function submitTask() {
    if (!currentTaskId) return;
    const formData = new FormData();

    if (currentTaskType === 'manual') {
        const fileBlock = document.getElementById('file-upload-block');
        const urlBlock = document.getElementById('url-input-block');
        const fileInput = document.getElementById('submission-file');
        const urlInput = document.getElementById('submission-url');

        let hasData = false;

        if (fileBlock && fileBlock.style.display !== 'none' && fileInput && fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0]);
            hasData = true;
        }
        if (urlBlock && urlBlock.style.display !== 'none' && urlInput && urlInput.value.trim()) {
            formData.append('submission_url', urlInput.value.trim());
            hasData = true;
        }

        if (!hasData) return alert('Пожалуйста, прикрепите файл или вставьте ссылку.');
    } else {
        formData.append('submission_url', 'auto_check_vk');
    }

    try {
        const res = await fetch(`${API_URL}/api/tasks/${currentTaskId}/submit`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
            body: formData
        });

        if (res.ok) {
            const result = await res.json();
            alert(result.message || 'Работа успешно отправлена!');
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
