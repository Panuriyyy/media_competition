const API_URL = 'http://127.0.0.1:8001';

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (!token) return window.location.href = 'login.html';
    
    loadAdminInfo();
    loadDashboard();
    loadTasks();
    loadSubmissions();
    loadRating();
    setupCreateForm();

    const typeSelect = document.getElementById('edit-task-type');
    if (typeSelect) typeSelect.addEventListener('change', toggleTaskTypeSettings);
});

function escapeHtml(str) {
    return str ? str.replace(/[&<>]/g, m => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[m])) : '';
}

// ========== ПРОФИЛЬ И ДАШБОРД ==========

async function loadAdminInfo() {
    try {
        const res = await fetch(`${API_URL}/api/users/me`, { 
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } 
        });
        if (res.ok) {
            const user = await res.json();
            document.getElementById('admin-name').textContent = user.full_name;
        }
    } catch (e) { console.error(e); }
}

function showMainTab(tabName) {
    document.querySelectorAll('.main-tab').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.tab-block').forEach(b => b.style.display = 'none');
    document.getElementById(`${tabName}-block`).style.display = 'block';

    if (tabName === 'dashboard') loadDashboard();
    if (tabName === 'tasks') loadTasks();
    if (tabName === 'submissions') loadSubmissions();
    if (tabName === 'rating') loadRating();
    if (tabName === 'about') loadAbout();
    if (tabName === 'faq') loadFaqAdmin();
}

// ========== ДАШБОРД: статистика по заданиям ==========

async function loadDashboard() {
    try {
        const res = await fetch(`${API_URL}/api/stats/dashboard`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) {
            const data = await res.json();
            document.getElementById('dash-users').textContent = data.total_users;
            document.getElementById('institutes-list').innerHTML = data.institutes_activity.map(i =>
                `<div class="stat-row"><span>${escapeHtml(i.institute)}</span><strong>${i.count} чел.</strong></div>`
            ).join('');

            const tasksList = document.getElementById('tasks-stats-list');
            if (tasksList) {
                if (!data.tasks_stats || !data.tasks_stats.length) {
                    tasksList.innerHTML = '<p style="opacity:0.6;">Заданий нет</p>';
                } else {
                    tasksList.innerHTML = data.tasks_stats.map(t => `
                        <div class="stat-row">
                            <span>${escapeHtml(t.title)}</span>
                            <strong>${t.completed_count} участн.</strong>
                        </div>`
                    ).join('');
                }
            }
        }
    } catch (e) { console.error(e); }
}

// ========== ЗАДАНИЯ ==========

function switchTaskStatus(status) {
    document.getElementById('tab-btn-active').classList.toggle('active', status === 'active');
    document.getElementById('tab-btn-archived').classList.toggle('active', status === 'archived');
    document.getElementById('active-tasks').style.display = status === 'active' ? 'grid' : 'none';
    document.getElementById('archived-tasks').style.display = status === 'archived' ? 'grid' : 'none';
}

async function loadTasks() {
    try {
        const res = await fetch(`${API_URL}/api/tasks`, { 
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } 
        });
        const tasks = await res.json();
        
        const render = (list, isArch) => list.length === 0 ? '<p>Заданий нет</p>' : list.map(t => `
            <div class="task-card" style="${isArch ? 'opacity: 0.7;' : ''}">
                <div class="task-info">
                    <h3>${escapeHtml(t.title)}</h3>
                    <p>${escapeHtml(t.description).replace(/\n/g, '<br>')}</p>
                    <div class="task-meta">
                        <span>★ ${t.points_at_stake} баллов</span>
                        <span class="type-badge">${t.task_type === 'auto' ? 'Авто' : 'Ручная'}</span>
                    </div>
                </div>
                <div class="task-actions">
                    ${!isArch ? `
                        <button onclick='openEditExistingModal(${JSON.stringify(t)})'>Изменить</button>
                        <button class="btn-danger" onclick="archiveTask(${t.id})">В архив</button>
                    ` : `
                        <button class="btn-danger" onclick="deleteTask(${t.id})">Удалить</button>
                    `}
                </div>
            </div>
        `).join('');

        document.getElementById('active-tasks').innerHTML = render(tasks.filter(t => t.is_active), false);
        document.getElementById('archived-tasks').innerHTML = render(tasks.filter(t => !t.is_active), true);
    } catch (e) { console.error(e); }
}

async function archiveTask(id) {
    if (!confirm('Перенести задание в архив?')) return;
    await fetch(`${API_URL}/api/admin/tasks/${id}/archive`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    loadTasks();
}

async function deleteTask(id) {
    if (!confirm('Удалить задание безвозвратно? Все связанные работы будут удалены.')) return;
    const res = await fetch(`${API_URL}/api/admin/tasks/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    if (res.ok) loadTasks();
    else alert('Ошибка удаления');
}

// ========== ПРОВЕРКА РАБОТ ==========

function renderFileLinks(data) {
    if (!data) return '—';
    if (data.startsWith('auto_check')) {
        return '<span style="opacity:0.6; font-style:italic;">Авто-проверка ВК</span>';
    }
    if (data.startsWith('http')) {
        return `<a href="${escapeHtml(data)}" target="_blank">Ссылка</a>`;
    }
    try {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed)) {
            return parsed.map((p, i) =>
                `<a href="${API_URL}${p}" target="_blank" style="display:inline-block; margin:2px 4px 2px 0; padding:2px 8px; background:rgba(255,255,255,0.15); border-radius:4px; font-size:12px;">Файл ${i + 1}</a>`
            ).join('');
        }
    } catch {}
    return `<a href="${API_URL}${data}" target="_blank">Файл</a>`;
}

async function loadSubmissions() {
    const tbody = document.getElementById('submissions-table-body');
    const filter = document.getElementById('status-filter').value;
    tbody.innerHTML = '<tr><td colspan="6">Загрузка...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/api/admin/submissions`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        let subs = await res.json();
        if (filter !== 'all') subs = subs.filter(s => s.status === filter);

        if (subs.length === 0) return tbody.innerHTML = '<tr><td colspan="6">Работ нет</td></tr>';

        const isAuto = s => s.submission_data && s.submission_data.startsWith('auto_check');

        tbody.innerHTML = subs.map(s => `
            <tr>
                <td><strong>${escapeHtml(s.user_name)}</strong></td>
                <td>${escapeHtml(s.task_title)}</td>
                <td>${renderFileLinks(s.submission_data)}</td>
                <td>${isAuto(s) ? (() => {
                    const statusMap = {pending: 'Ожидает', approved: 'Принято', rejected: 'Отклонено'};
                    const color = s.status === 'approved' ? '#a5d6a7' : s.status === 'rejected' ? '#ff8a80' : '#ffcc80';
                    return `<span style="color:${color}; font-size:13px;">${statusMap[s.status] || s.status}</span>`;
                })() : `<select onchange="updateSubStatus(${s.id}, this.value)" class="table-select">
                        <option value="pending" ${s.status === 'pending' ? 'selected' : ''}>Ожидает</option>
                        <option value="approved" ${s.status === 'approved' ? 'selected' : ''}>Принято</option>
                        <option value="rejected" ${s.status === 'rejected' ? 'selected' : ''}>Отклонено</option>
                    </select>`}
                </td>
                <td>
                    ${isAuto(s)
                        ? `<span style="font-weight:600;">${s.score}</span> <span style="font-size:11px; opacity:0.6;">/ ${s.max_points}</span>`
                        : `<input type="number" value="${s.score}" onchange="updateSubScore(${s.id}, this.value)" class="table-input" style="width:60px;">
                           <span style="font-size:11px; opacity:0.6;">/ ${s.max_points}</span>`}
                </td>
                <td>${isAuto(s) ? '' : `<button class="save-small-btn" onclick="saveReview(${s.id})">Ок</button>`}</td>
            </tr>
        `).join('');
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6">Ошибка загрузки</td></tr>'; }
}

let reviewChanges = {};
function updateSubStatus(id, val) { reviewChanges[id] = { ...reviewChanges[id], status: val }; }
function updateSubScore(id, val) { reviewChanges[id] = { ...reviewChanges[id], score: parseFloat(val) }; }

async function saveReview(id) {
    if (!reviewChanges[id]) return alert('Нет изменений для сохранения');
    const fd = new FormData();
    fd.append('status', reviewChanges[id].status || 'pending');
    fd.append('score', reviewChanges[id].score || 0);
    
    const res = await fetch(`${API_URL}/api/submissions/${id}/review`, { 
        method: 'POST', 
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }, 
        body: fd 
    });
    if (res.ok) { alert('Оценка сохранена!'); loadSubmissions(); loadRating(); }
}

// ========== РЕЙТИНГ ==========

async function loadRating() {
    const tbody = document.getElementById('rating-table-body');
    if (!tbody) return;
    try {
        const res = await fetch(`${API_URL}/api/rating`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        const ratings = data.ratings || [];

        if (!ratings.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Нет данных</td></tr>';
            return;
        }

        tbody.innerHTML = ratings.map((r, i) => `
            <tr>
                <td>${i + 1}</td>
                <td>${escapeHtml(r.full_name)}</td>
                <td>${escapeHtml(r.institute)}</td>
                <td><strong>${r.total_score}</strong></td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

// ========== СОЗДАНИЕ ЗАДАНИЯ ==========

function toggleTaskTypeSettings() {
    const isAuto = document.getElementById('edit-task-type').value === 'auto';
    document.getElementById('auto-options').style.display = isAuto ? 'block' : 'none';
    document.getElementById('format-block').style.display = isAuto ? 'none' : 'block';
    document.getElementById('points-container').style.display = isAuto ? 'none' : 'block';
}

function openCreateTaskModal() {
    document.getElementById('editTaskForm').reset();
    document.getElementById('dynamic-links-list').innerHTML = '';
    addLinkInput();
    toggleTaskTypeSettings();
    document.getElementById('editTaskModal').style.display = 'flex';
}

function closeEditModal() { document.getElementById('editTaskModal').style.display = 'none'; }

function setupCreateForm() {
    document.getElementById('editTaskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const isAuto = document.getElementById('edit-task-type').value === 'auto';
        const autoType = document.getElementById('edit-auto-type').value;
        const format = document.getElementById('edit-formats').value;
        
        let desc = document.getElementById('edit-desc').value;
        if (!isAuto) desc += `\n\nФОРМАТ: ${format}`;

        const links = Array.from(document.querySelectorAll('.dynamic-link-input')).map(i => i.value.trim()).filter(v => v);
        
        // Автоматический расчет баллов
        let points = isAuto ? links.length * (autoType === 'likes' ? 1 : 3) : parseFloat(document.getElementById('edit-points').value) || 0;

        const payload = {
            title: document.getElementById('edit-title').value,
            description: desc,
            task_type: document.getElementById('edit-task-type').value,
            auto_type: isAuto ? autoType : null,
            points_at_stake: points,
            deadline: document.getElementById('edit-deadline').value + ":00",
            posts_urls: isAuto ? links : [],
            format_type: isAuto ? null : format
        };

        const res = await fetch(`${API_URL}/api/tasks`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, 
            body: JSON.stringify(payload) 
        });
        
        if (res.ok) { alert('Задание создано!'); closeEditModal(); loadTasks(); }
        else { const err = await res.json(); alert(`Ошибка: ${err.detail}`); }
    });
}

function addLinkInput() {
    const div = document.createElement('div');
    div.className = 'link-input-group';
    div.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px;';
    div.innerHTML = `
        <input type="url" class="dynamic-link-input" placeholder="https://vk.com/wall..." style="flex: 1; padding: 8px; border-radius: 4px; border: none;">
        <button type="button" onclick="this.parentElement.remove()" style="background: #ff4444; color: white; border: none; padding: 0 15px; border-radius: 4px; cursor: pointer;">&times;</button>`;
    document.getElementById('dynamic-links-list').appendChild(div);
}

function downloadReport(f) {
    fetch(`${API_URL}/api/reports/${f}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
    .then(r => r.blob()).then(b => {
        const a = document.createElement('a');
        a.href = window.URL.createObjectURL(b);
        a.download = `rating.${f}`;
        a.click();
    });
}

function logout() { localStorage.clear(); window.location.href = 'login.html'; }

// ========== РЕДАКТИРОВАНИЕ ЗАДАНИЯ ==========

function openEditExistingModal(task) {
    document.getElementById('edit-existing-id').value = task.id;
    document.getElementById('edit-existing-title').value = task.title;
    document.getElementById('edit-existing-desc').value = task.description;
    document.getElementById('edit-existing-deadline').value = task.deadline
        ? task.deadline.replace('Z','').slice(0,16) : '';
    document.getElementById('edit-existing-type').value = task.task_type;
    document.getElementById('edit-existing-auto-type').value = task.auto_type || 'likes';
    document.getElementById('edit-existing-points').value = task.points_at_stake || 10;

    // Заполняем ссылки для авто-заданий
    const linksList = document.getElementById('edit-existing-links-list');
    linksList.innerHTML = '';
    const urls = Array.isArray(task.posts_urls) ? task.posts_urls : [];
    if (urls.length) {
        urls.forEach(u => addExistingLinkInput(u));
    } else {
        addExistingLinkInput();
    }

    toggleExistingTypeSettings();
    document.getElementById('editExistingTaskModal').style.display = 'flex';
}

function closeEditExistingModal() {
    document.getElementById('editExistingTaskModal').style.display = 'none';
}

function toggleExistingTypeSettings() {
    const isAuto = document.getElementById('edit-existing-type').value === 'auto';
    document.getElementById('edit-existing-auto-options').style.display = isAuto ? 'block' : 'none';
    document.getElementById('edit-existing-format-block').style.display = isAuto ? 'none' : 'block';
    document.getElementById('edit-existing-points-container').style.display = isAuto ? 'none' : 'block';
}

function addExistingLinkInput(value = '') {
    const div = document.createElement('div');
    div.style.cssText = 'display:flex; gap:10px; margin-bottom:10px;';
    div.innerHTML = `
        <input type="url" class="existing-link-input" value="${escapeHtml(value)}"
            placeholder="https://vk.com/wall..." style="flex:1; padding:8px; border-radius:4px; border:none;">
        <button type="button" onclick="this.parentElement.remove()"
            style="background:#ff4444; color:white; border:none; padding:0 15px; border-radius:4px; cursor:pointer;">&times;</button>`;
    document.getElementById('edit-existing-links-list').appendChild(div);
}

document.getElementById('editExistingTaskForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-existing-id').value;
    const isAuto = document.getElementById('edit-existing-type').value === 'auto';
    const autoType = document.getElementById('edit-existing-auto-type').value;
    const format = document.getElementById('edit-existing-format').value;
    const links = Array.from(document.querySelectorAll('.existing-link-input'))
        .map(i => i.value.trim()).filter(v => v);
    const points = isAuto
        ? links.length * (autoType === 'likes' ? 1 : 3)
        : parseFloat(document.getElementById('edit-existing-points').value) || 0;

    const payload = {
        title: document.getElementById('edit-existing-title').value,
        description: document.getElementById('edit-existing-desc').value,
        task_type: document.getElementById('edit-existing-type').value,
        auto_type: isAuto ? autoType : null,
        points_at_stake: points,
        deadline: document.getElementById('edit-existing-deadline').value + ':00',
        posts_urls: isAuto ? links : [],
        format_type: isAuto ? null : format,
    };

    const res = await fetch(`${API_URL}/api/tasks/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify(payload),
    });

    if (res.ok) {
        closeEditExistingModal();
        loadTasks();
    } else {
        const err = await res.json();
        alert(`Ошибка: ${err.detail}`);
    }
});

// ========== О КОНКУРСЕ ==========

async function loadAbout() {
    try {
        const res = await fetch(`${API_URL}/api/about`);
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('about-view').textContent = data.content || '(Текст о конкурсе не заполнен)';
        document.getElementById('about-textarea').value = data.content || '';

        const newsList = document.getElementById('news-list');
        if (!data.news.length) {
            newsList.innerHTML = '<p style="opacity:0.6;">Новостей нет</p>';
        } else {
            newsList.innerHTML = data.news.map(n => `
                <div style="background:rgba(255,255,255,0.07); border-radius:8px; padding:15px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <strong>${escapeHtml(n.title)}</strong>
                        <div style="display:flex; gap:8px; flex-shrink:0; margin-left:15px;">
                            <button class="save-small-btn" onclick="openNewsModal(${JSON.stringify(n).replace(/'/g, '&#39;')})">Изм.</button>
                            <button class="archive-btn" onclick="deleteNews(${n.id})">Удал.</button>
                        </div>
                    </div>
                    <p style="margin-top:8px; opacity:0.85; white-space:pre-wrap;">${escapeHtml(n.content)}</p>
                    <small style="opacity:0.5;">${new Date(n.created_at).toLocaleDateString()}</small>
                </div>`
            ).join('');
        }
    } catch (e) { console.error(e); }
}

function toggleAboutEdit() {
    const view = document.getElementById('about-view');
    const edit = document.getElementById('about-edit');
    const isEditing = edit.style.display !== 'none';
    view.style.display = isEditing ? 'block' : 'none';
    edit.style.display = isEditing ? 'none' : 'block';
}

async function saveAbout() {
    const content = document.getElementById('about-textarea').value;
    const fd = new FormData();
    fd.append('content', content);
    const res = await fetch(`${API_URL}/api/admin/about`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: fd,
    });
    if (res.ok) {
        document.getElementById('about-view').textContent = content;
        toggleAboutEdit();
    } else {
        alert('Ошибка сохранения');
    }
}

// Новости
function openNewsModal(news = null) {
    document.getElementById('news-edit-id').value = news ? news.id : '';
    document.getElementById('news-title-input').value = news ? news.title : '';
    document.getElementById('news-content-input').value = news ? news.content : '';
    document.getElementById('news-modal-title').textContent = news ? 'Редактировать новость' : 'Добавить новость';
    document.getElementById('newsModal').style.display = 'flex';
}

function closeNewsModal() { document.getElementById('newsModal').style.display = 'none'; }

document.getElementById('newsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('news-edit-id').value;
    const fd = new FormData();
    fd.append('title', document.getElementById('news-title-input').value);
    fd.append('content', document.getElementById('news-content-input').value);

    const url = id ? `${API_URL}/api/admin/news/${id}` : `${API_URL}/api/admin/news`;
    const method = id ? 'PUT' : 'POST';

    const res = await fetch(url, {
        method,
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: fd,
    });
    if (res.ok) { closeNewsModal(); loadAbout(); }
    else { const err = await res.json(); alert(`Ошибка: ${err.detail}`); }
});

async function deleteNews(id) {
    if (!confirm('Удалить новость?')) return;
    await fetch(`${API_URL}/api/admin/news/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
    });
    loadAbout();
}

// ========== FAQ ==========

async function loadFaqAdmin() {
    try {
        const res = await fetch(`${API_URL}/api/faq`);
        if (!res.ok) return;
        const items = await res.json();
        const list = document.getElementById('faq-admin-list');
        if (!items.length) {
            list.innerHTML = '<p style="opacity:0.6;">Вопросов нет. Добавьте первый!</p>';
            return;
        }
        list.innerHTML = items.map(f => `
            <div style="background:rgba(255,255,255,0.07); border-radius:8px; padding:15px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <strong>${escapeHtml(f.question)}</strong>
                    <div style="display:flex; gap:8px; flex-shrink:0; margin-left:15px;">
                        <button class="save-small-btn" onclick="openFaqModal(${JSON.stringify(f).replace(/'/g,'&#39;')})">Изм.</button>
                        <button class="archive-btn" onclick="deleteFaq(${f.id})">Удал.</button>
                    </div>
                </div>
                <p style="margin-top:8px; opacity:0.85; white-space:pre-wrap;">${escapeHtml(f.answer)}</p>
            </div>`
        ).join('');
    } catch (e) { console.error(e); }
}

function openFaqModal(item = null) {
    document.getElementById('faq-edit-id').value = item ? item.id : '';
    document.getElementById('faq-question-input').value = item ? item.question : '';
    document.getElementById('faq-answer-input').value = item ? item.answer : '';
    document.getElementById('faq-order-input').value = item ? (item.order_num || 0) : 0;
    document.getElementById('faq-modal-title').textContent = item ? 'Редактировать вопрос' : 'Добавить вопрос';
    document.getElementById('faqModal').style.display = 'flex';
}

function closeFaqModal() { document.getElementById('faqModal').style.display = 'none'; }

document.getElementById('faqForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('faq-edit-id').value;
    const fd = new FormData();
    fd.append('question', document.getElementById('faq-question-input').value);
    fd.append('answer', document.getElementById('faq-answer-input').value);
    fd.append('order_num', document.getElementById('faq-order-input').value || 0);

    const url = id ? `${API_URL}/api/admin/faq/${id}` : `${API_URL}/api/admin/faq`;
    const method = id ? 'PUT' : 'POST';

    const res = await fetch(url, {
        method,
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: fd,
    });
    if (res.ok) { closeFaqModal(); loadFaqAdmin(); }
    else { const err = await res.json(); alert(`Ошибка: ${err.detail}`); }
});

async function deleteFaq(id) {
    if (!confirm('Удалить вопрос?')) return;
    await fetch(`${API_URL}/api/admin/faq/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
    });
    loadFaqAdmin();
}