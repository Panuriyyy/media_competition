document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const messageDiv = document.getElementById('message');
    
    if (!username || !password) {
        messageDiv.textContent = 'Пожалуйста, заполните все поля';
        messageDiv.className = 'message error';
        return;
    }
    
    try {
        const response = await fetch('http://127.0.0.1:8001/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            messageDiv.textContent = `Добро пожаловать, ${data.user.full_name}!`;
            messageDiv.className = 'message success';
            
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            
            setTimeout(() => {
                window.location.href = 'admin.html';  // УБЕДИТЕСЬ, ЧТО ЗДЕСЬ admin.html
            }, 1500);
        } else {
            messageDiv.textContent = data.detail || 'Ошибка входа';
            messageDiv.className = 'message error';
        }
    } catch (error) {
        messageDiv.textContent = 'Ошибка подключения к серверу';
        messageDiv.className = 'message error';
    }
});

document.getElementById('loginForm').addEventListener('reset', function() {
    document.getElementById('message').style.display = 'none';
});