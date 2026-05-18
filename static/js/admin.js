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
        const res = await fetch(`${API_URL}/api/admin/tasks`, { 
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
                    ${!isArch ? `<button class="archive-btn" onclick="archiveTask(${t.id})">В архив</button>` : '<span>Архивировано</span>'}
                </div>
            </div>
        `).join('');

        document.getElementById('active-tasks').innerHTML = render(tasks.filter(t => t.is_active), false);
        document.getElementById('archived-tasks').innerHTML = render(tasks.filter(t => !t.is_active), true);
    } catch (e) { console.error(e); }
}

async function archiveTask(id) {
    if (!confirm("Перенести в архив?")) return;
    await fetch(`${API_URL}/api/admin/tasks/${id}/archive`, { 
        method: 'POST', 
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } 
    });
    loadTasks();
}

// ========== ПРОВЕРКА РАБОТ ==========

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
        
        tbody.innerHTML = subs.map(s => `
            <tr>
                <td><strong>${escapeHtml(s.user_name)}</strong></td>
                <td>${escapeHtml(s.task_title)}</td>
                <td>${s.submission_data.startsWith('http') ? `<a href="${s.submission_data}" target="_blank">Ссылка</a>` : `<a href="${API_URL}${s.submission_data}" target="_blank">Файл</a>`}</td>
                <td>
                    <select onchange="updateSubStatus(${s.id}, this.value)" class="table-select">
                        <option value="pending" ${s.status === 'pending' ? 'selected' : ''}>Ожидает</option>
                        <option value="approved" ${s.status === 'approved' ? 'selected' : ''}>Принято</option>
                        <option value="rejected" ${s.status === 'rejected' ? 'selected' : ''}>Отклонено</option>
                    </select>
                </td>
                <td>
                    <input type="number" value="${s.score}" onchange="updateSubScore(${s.id}, this.value)" class="table-input" style="width: 60px;">
                    <span style="font-size: 11px; opacity: 0.6;">/ ${s.max_points}</span>
                </td>
                <td><button class="save-small-btn" onclick="saveReview(${s.id})">Ок</button></td>
            </tr>
        `).join('');
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6">Ошибка загрузки</td></tr>'; }
}

let reviewChanges = {};
function updateSubStatus(id, val) { reviewChanges[id] = { ...reviewChanges[id], status: val }; }
function updateSubScore(id, val) { reviewChanges[id] = { ...reviewChanges[id], score: parseFloat(val) }; }

async function saveReview(id) {
    if (!reviewChanges[id]) return alert('Нет изменений');
    const fd = new FormData();
    fd.append('status', reviewChanges[id].status || 'pending');
    fd.append('score', reviewChanges[id].score || 0);
    
    const res = await fetch(`${API_URL}/api/submissions/${id}/review`, { 
        method: 'POST', 
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }, 
        body: fd 
    });
    if (res.ok) { alert('Сохранено!'); loadSubmissions(); loadRating(); }
}

// ========== РЕЙТИНГ ==========

async function loadRating() {
    const tbody = document.getElementById('rating-table-body');
    if (!tbody) return;
    try {
        const res = await fetch(`${API_URL}/api/reports/csv`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        const text = await res.text();
        const rows = text.split('\n').slice(1).filter(r => r.trim());
        
        const sorted = rows.map(r => r.split(';')).sort((a, b) => b[2] - a[2]);

        tbody.innerHTML = sorted.map((r, i) => `
            <tr>
                <td>${i + 1}</td>
                <td>${escapeHtml(r[0])}</td>
                <td>${escapeHtml(r[1])}</td>
                <td><strong>${r[2]}</strong></td>
            </tr>
        `).join('');
    } catch (e) {}
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
            posts_urls: isAuto ? links : []
        };

        const res = await fetch(`${API_URL}/api/tasks`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, 
            body: JSON.stringify(payload) 
        });
        
        if (res.ok) { alert('Создано!'); closeEditModal(); loadTasks(); }
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