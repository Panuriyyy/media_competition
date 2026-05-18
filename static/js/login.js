const API_URL = 'http://127.0.0.1:8001'; 

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
            redirectUrl: 'http://127.0.0.1:8001/static/login.html', // Для локального теста должен быть твой локальный адрес!
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
                localStorage.setItem('token', data.access_token);
                window.location.href = data.role === 'admin' ? 'admin.html' : 'user.html';
            } else {
                messageDiv.className = 'message error';
                messageDiv.textContent = data.detail || 'Ошибка авторизации';
                messageDiv.style.color = '#ff4444';
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