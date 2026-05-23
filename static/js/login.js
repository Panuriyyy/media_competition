const API_URL = '';
let loginAttempts = 0;
const MAX_LOGIN_ATTEMPTS = 3;
let _resetVkToken = null;

document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (token) {
        checkTokenAndRedirect(token);
    }
    
// ==========================================
    // ВХОД ЧЕРЕЗ VK ID (LOW-CODE ВИДЖЕТ)
    // ==========================================
    if ('VKIDSDK' in window) {
        const VKID = window.VKIDSDK;

        VKID.Config.init({
            app: 54503107, // Твой ID приложения
            redirectUrl: 'https://mediacompetitionspbstu.ru/static/login.html',
            responseMode: VKID.ConfigResponseMode.Callback,
            source: VKID.ConfigSource.LOWCODE,
        });

        const oneTap = new VKID.OneTap();
        const container = document.getElementById('VkIdSdkOneTap');

        if (container) {
            oneTap.render({
                container: container,
                showAlternativeLogin: true
            })
            .on(VKID.WidgetEvents.ERROR, function(error) {
                console.error('Ошибка виджета VK:', error);
            })
            .on(VKID.OneTapInternalEvents.LOGIN_SUCCESS, function (payload) {
                const code = payload.code;
                const deviceId = payload.device_id;

                // Меняем код на токен ВК
                VKID.Auth.exchangeCode(code, deviceId)
                    .then(vkidOnSuccess)
                    .catch(function(err) { console.error('Ошибка обмена кода:', err); });
            });
        }

        // Эта функция срабатывает, когда ВК успешно авторизовал пользователя
        async function vkidOnSuccess(data) {
            try {
                // Отправляем токен ВКонтакте на НАШ сервер для проверки и входа
                const response = await fetch(`${API_URL}/api/auth/vk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        access_token: data.access_token,
                        user_id: data.user_id
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    // Сервер нас пустил! Сохраняем токен и заходим
                    localStorage.setItem('token', result.access_token);
                    window.location.href = result.role === 'admin' ? 'admin.html' : 'user.html';
                } else {
                    alert('Ошибка сервера: ' + result.detail);
                }
            } catch (error) {
                alert('Сбой сети при входе через ВКонтакте');
            }
        }
    }

    // Классический вход
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const messageDiv = document.getElementById('login-message');
        
        try {
            const response = await fetch(`${API_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                loginAttempts = 0;
                localStorage.setItem('token', data.access_token);
                window.location.href = data.role === 'admin' ? 'admin.html' : 'user.html';
            } else {
                loginAttempts++;
                messageDiv.className = 'message error';
                messageDiv.style.color = '#ff4444';
                if (loginAttempts >= MAX_LOGIN_ATTEMPTS) {
                    loginAttempts = 0;
                    messageDiv.innerHTML = `Неверный логин или пароль. <a href="#" onclick="openForgotPasswordModal(); return false;" style="color:#7ddf84; text-decoration:underline;">Восстановить пароль?</a>`;
                } else {
                    messageDiv.textContent = `${data.detail || 'Неверный логин или пароль'} (попытка ${loginAttempts} из ${MAX_LOGIN_ATTEMPTS})`;
                }
            }
        } catch (error) {
            messageDiv.className = 'message error';
            messageDiv.textContent = 'Ошибка подключения к серверу';
        }
    });

    // Регистрация
    document.getElementById('registerForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const messageDiv = document.getElementById('register-message');
        
        const formData = {
            full_name: document.getElementById('reg-fullname').value,
            username: document.getElementById('reg-username').value,
            email: document.getElementById('reg-email').value,
            password: document.getElementById('reg-password').value,
            institute: document.getElementById('reg-institute').value,
            vk_link: document.getElementById('reg-vk').value,
            tg_link: document.getElementById('reg-tg').value
        };

        try {
            const response = await fetch(`${API_URL}/api/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                messageDiv.className = 'message success';
                messageDiv.textContent = 'Регистрация успешна! Теперь войдите в систему.';
                messageDiv.style.color = '#4CAF50';
                document.getElementById('registerForm').reset();
                setTimeout(() => showAuthTab('login'), 2000);
            } else {
                messageDiv.className = 'message error';
                messageDiv.textContent = data.detail || 'Ошибка регистрации';
                messageDiv.style.color = '#ff4444';
            }
        } catch (error) {
            messageDiv.textContent = 'Ошибка сервера';
        }
    });
});

async function checkTokenAndRedirect(token) {
    try {
        const res = await fetch(`${API_URL}/api/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const user = await res.json();
            window.location.href = user.role === 'admin' ? 'admin.html' : 'user.html';
        } else {
            localStorage.removeItem('token');
        }
    } catch (e) { localStorage.removeItem('token'); }
}

function showAuthTab(tabName) {
    document.getElementById('login-tab').style.display = tabName === 'login' ? 'block' : 'none';
    document.getElementById('register-tab').style.display = tabName === 'register' ? 'block' : 'none';
    const btns = document.querySelectorAll('.tab-btn');
    btns[0].classList.toggle('active', tabName === 'login');
    btns[1].classList.toggle('active', tabName === 'register');
}

// ==========================================
// ВОССТАНОВЛЕНИЕ ПАРОЛЯ ЧЕРЕЗ VK
// ==========================================

function openForgotPasswordModal() {
    _resetVkToken = null;
    document.getElementById('reset-vk-section').style.display = 'block';
    document.getElementById('reset-password-section').style.display = 'none';
    document.getElementById('reset-vk-error').textContent = '';
    document.getElementById('reset-password-msg').textContent = '';
    document.getElementById('new-password').value = '';
    document.getElementById('confirm-password').value = '';
    document.getElementById('forgot-modal').style.display = 'flex';
    initResetVkWidget();
}

function closeForgotPasswordModal() {
    document.getElementById('forgot-modal').style.display = 'none';
    _resetVkToken = null;
}

function initResetVkWidget() {
    if (!('VKIDSDK' in window)) {
        document.getElementById('reset-vk-error').textContent = 'VK ID SDK недоступен. Попробуйте обновить страницу.';
        return;
    }
    const VKID = window.VKIDSDK;
    const container = document.getElementById('VkIdSdkReset');
    if (!container) return;
    container.innerHTML = '';

    const resetOneTap = new VKID.OneTap();
    resetOneTap.render({ container: container, showAlternativeLogin: false })
        .on(VKID.WidgetEvents.ERROR, function (error) {
            document.getElementById('reset-vk-error').textContent = 'Ошибка VK: ' + (error.text || 'неизвестная ошибка');
        })
        .on(VKID.OneTapInternalEvents.LOGIN_SUCCESS, function (payload) {
            VKID.Auth.exchangeCode(payload.code, payload.device_id)
                .then(handleResetVkAuth)
                .catch(function () {
                    document.getElementById('reset-vk-error').textContent = 'Ошибка получения токена VK. Попробуйте ещё раз.';
                });
        });
}

async function handleResetVkAuth(data) {
    _resetVkToken = data.access_token;
    document.getElementById('reset-vk-section').style.display = 'none';
    document.getElementById('reset-password-section').style.display = 'block';
    document.getElementById('reset-user-name').textContent = '';
}

async function submitNewPassword() {
    const newPass = document.getElementById('new-password').value;
    const confirmPass = document.getElementById('confirm-password').value;
    const msgDiv = document.getElementById('reset-password-msg');

    msgDiv.style.color = '#ff6b6b';

    if (newPass.length < 6) {
        msgDiv.textContent = 'Пароль должен содержать не менее 6 символов';
        return;
    }
    if (newPass !== confirmPass) {
        msgDiv.textContent = 'Пароли не совпадают';
        return;
    }
    if (!_resetVkToken) {
        msgDiv.textContent = 'Сессия истекла. Закройте окно и попробуйте снова.';
        return;
    }

    try {
        const res = await fetch(`${API_URL}/api/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ access_token: _resetVkToken, new_password: newPass }),
        });
        const result = await res.json();

        if (res.ok) {
            msgDiv.style.color = '#4CAF50';
            msgDiv.textContent = 'Пароль успешно изменён!';
            setTimeout(() => {
                closeForgotPasswordModal();
                showAuthTab('login');
            }, 1800);
        } else {
            msgDiv.textContent = result.detail || 'Ошибка сохранения пароля';
        }
    } catch (e) {
        msgDiv.textContent = 'Ошибка подключения к серверу';
    }
}