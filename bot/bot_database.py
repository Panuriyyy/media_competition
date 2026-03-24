"""
bot_database.py - Модуль для работы с базой данных из VK бота
"""

import sqlite3
from datetime import datetime, timedelta
import requests
import os
from typing import List, Dict, Optional, Tuple
from config import API_URL, ADMIN_USERNAME, ADMIN_PASSWORD

# Конфигурация
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "users.db")
API_URL = "http://127.0.0.1:8001"  # URL вашего FastAPI сервера

# Хранилище для токена
_token_cache = {"token": None, "expires_at": None}


def get_api_token() -> Optional[str]:
    """
    Получает токен для доступа к API, логинясь под администратора.
    Токен кэшируется и автоматически обновляется при истечении.
    """
    global _token_cache

    # Проверяем, есть ли уже валидный токен
    if _token_cache["token"] and _token_cache["expires_at"]:
        if datetime.now() < _token_cache["expires_at"]:
            return _token_cache["token"]

    try:
        print(f"🔑 Получение нового токена для {ADMIN_USERNAME}...")

        # Логинимся как администратор
        response = requests.post(
            f"{API_URL}/api/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]

            # Токен живёт 30 минут (из auth.py), кэшируем на 25 минут
            expires_at = datetime.now() + timedelta(minutes=25)

            _token_cache["token"] = token
            _token_cache["expires_at"] = expires_at

            print(f"✅ Получен новый токен доступа для {ADMIN_USERNAME}")
            return token
        else:
            print(f"❌ Ошибка получения токена: {response.status_code}")
            if response.status_code == 401:
                print("   Неверные учетные данные для администратора")
            return None

    except requests.exceptions.ConnectionError:
        print(f"❌ Нет подключения к API по адресу {API_URL}")
        return None
    except Exception as e:
        print(f"❌ Ошибка при получении токена: {e}")
        return None


def init_bot_tables():
    """Создает таблицы для бота в общей БД, если их нет."""
    conn = None
    try:
        if not os.path.exists(DB_PATH):
            print(f"⚠️ Файл БД не найден по пути: {DB_PATH}")
            print(f"📁 Абсолютный путь к БД: {os.path.abspath(DB_PATH)}")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Таблица пользователей бота
        c.execute(
            """CREATE TABLE IF NOT EXISTS bot_users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      vk_id INTEGER UNIQUE,
                      name TEXT NOT NULL,
                      institute TEXT,
                      group_num TEXT,
                      reg_date TIMESTAMP,
                      is_active INTEGER DEFAULT 1)"""
        )

        # Таблица для отслеживания отправленных уведомлений
        c.execute(
            """CREATE TABLE IF NOT EXISTS sent_notifications
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_vk_id INTEGER,
                      task_id INTEGER,
                      sent_date TIMESTAMP,
                      UNIQUE(user_vk_id, task_id))"""
        )

        # Таблица для выполнения заданий пользователями
        c.execute(
            """CREATE TABLE IF NOT EXISTS user_tasks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_vk_id INTEGER,
                      task_id INTEGER,
                      status TEXT,
                      completed_date TIMESTAMP,
                      UNIQUE(user_vk_id, task_id))"""
        )

        # Таблица для ручных отправок
        c.execute(
            """CREATE TABLE IF NOT EXISTS manual_submissions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_vk_id INTEGER,
                      task_id INTEGER,
                      submission_url TEXT,
                      submission_type TEXT,
                      submission_date TIMESTAMP,
                      status TEXT DEFAULT 'pending')"""
        )

        conn.commit()
        print(f"✅ Таблицы бота созданы/проверены в {DB_PATH}")

        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        print(f"📊 Таблицы в БД: {[t[0] for t in tables]}")

    except sqlite3.Error as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
    finally:
        if conn:
            conn.close()


def save_user(vk_id: int, name: str, institute: str, group_num: str) -> bool:
    """Сохраняет или обновляет пользователя бота в БД."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT id FROM bot_users WHERE vk_id = ?", (vk_id,))
        existing = c.fetchone()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existing:
            c.execute(
                """UPDATE bot_users 
                         SET name = ?, institute = ?, group_num = ?, reg_date = ?, is_active = 1
                         WHERE vk_id = ?""",
                (name, institute, group_num, now, vk_id),
            )
            print(f"🔄 Пользователь {vk_id} обновлен в БД")
        else:
            c.execute(
                """INSERT INTO bot_users 
                         (vk_id, name, institute, group_num, reg_date, is_active)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                (vk_id, name, institute, group_num, now, 1),
            )
            print(f"✅ Новый пользователь {vk_id} сохранен в БД")

        conn.commit()
        return True

    except sqlite3.IntegrityError as e:
        print(f"❌ Ошибка целостности данных: {e}")
        return False
    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_all_users() -> List[int]:
    """Получает список VK ID всех активных пользователей."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT vk_id FROM bot_users WHERE is_active = 1")
        users = [row[0] for row in c.fetchall()]

        print(f"📊 Найдено {len(users)} активных пользователей")
        return users

    except sqlite3.Error as e:
        print(f"❌ Ошибка при получении пользователей: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_user_info(vk_id: int) -> Optional[Dict]:
    """Получает информацию о конкретном пользователе."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """SELECT vk_id, name, institute, group_num, reg_date, is_active 
                     FROM bot_users WHERE vk_id = ?""",
            (vk_id,),
        )
        row = c.fetchone()

        if row:
            return {
                "vk_id": row[0],
                "name": row[1],
                "institute": row[2],
                "group_num": row[3],
                "reg_date": row[4],
                "is_active": bool(row[5]),
            }
        return None

    except sqlite3.Error as e:
        print(f"❌ Ошибка при получении пользователя {vk_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def has_received_notification(user_vk_id: int, task_id: int) -> bool:
    """Проверяет, получал ли пользователь уведомление о задании."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            """SELECT id FROM sent_notifications 
                     WHERE user_vk_id = ? AND task_id = ?""",
            (user_vk_id, task_id),
        )
        result = c.fetchone()
        return result is not None

    except sqlite3.Error as e:
        print(f"❌ Ошибка при проверке уведомления: {e}")
        return False
    finally:
        if conn:
            conn.close()


def mark_notification_sent(user_vk_id: int, task_id: int) -> bool:
    """Отмечает, что уведомление о задании отправлено."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            """INSERT OR IGNORE INTO sent_notifications 
                     (user_vk_id, task_id, sent_date)
                     VALUES (?, ?, ?)""",
            (user_vk_id, task_id, now),
        )
        conn.commit()

        if c.rowcount > 0:
            print(
                f"📨 Отмечена отправка уведомления о задании {task_id} пользователю {user_vk_id}"
            )
            return True
        return False

    except sqlite3.Error as e:
        print(f"❌ Ошибка при отметке уведомления: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_active_tasks_from_api() -> List[Dict]:
    """
    Получает список активных заданий из API сайта.
    Автоматически получает и обновляет токен при необходимости.
    """
    # Получаем токен (автоматически обновится, если истёк)
    token = get_api_token()
    if not token:
        print("❌ Не удалось получить токен доступа к API")
        return []

    try:
        # Формируем заголовки с токеном авторизации
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        print(f"🔍 Запрос к API: {API_URL}/api/tasks")
        response = requests.get(f"{API_URL}/api/tasks", headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            tasks = data.get("tasks", [])

            # Фильтруем только активные задания с дедлайном в будущем
            now = datetime.now()
            active_tasks = []

            for task in tasks:
                if not task.get("is_active", False):
                    continue

                deadline_str = task.get("deadline", "")
                if deadline_str:
                    # Убираем 'Z' если есть и парсим
                    deadline_str = deadline_str.replace("Z", "")
                    try:
                        deadline = datetime.fromisoformat(deadline_str)
                        if deadline > now:
                            active_tasks.append(task)
                    except ValueError:
                        print(f"⚠️ Неверный формат даты: {deadline_str}")
                        continue

            print(f"✅ Получено {len(active_tasks)} активных заданий из API")
            return active_tasks

        elif response.status_code == 401:
            print(f"❌ Ошибка авторизации API (401). Токен истёк или недействителен")
            # Сбрасываем кэш токена, чтобы при следующем вызове получить новый
            global _token_cache
            _token_cache["token"] = None
            _token_cache["expires_at"] = None
            return []
        else:
            print(f"⚠️ API вернул код {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return []

    except requests.exceptions.ConnectionError:
        print(f"❌ Нет подключения к API по адресу {API_URL}")
        print(f"   Убедитесь, что сервер сайта запущен на порту 8001")
        return []
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут при подключении к API")
        return []
    except Exception as e:
        print(f"❌ Неожиданная ошибка при запросе к API: {e}")
        return []


def save_user_task_completion(user_vk_id: int, task_id: int, status: str) -> bool:
    """
    Сохраняет информацию о выполнении задания пользователем
    status: 'completed', 'pending', 'failed'
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            """INSERT OR REPLACE INTO user_tasks 
                     (user_vk_id, task_id, status, completed_date)
                     VALUES (?, ?, ?, ?)""",
            (user_vk_id, task_id, status, now),
        )

        conn.commit()
        print(
            f"✅ Задание {task_id} для пользователя {user_vk_id} отмечено как {status}"
        )
        return True

    except Exception as e:
        print(f"❌ Ошибка сохранения выполнения задания: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_user_task_status(user_vk_id: int, task_id: int) -> Optional[str]:
    """Получает статус выполнения задания пользователем."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            """SELECT status FROM user_tasks 
                     WHERE user_vk_id = ? AND task_id = ?""",
            (user_vk_id, task_id),
        )

        result = c.fetchone()
        return result[0] if result else None

    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")
        return None
    finally:
        if conn:
            conn.close()


def save_user_task_score(user_vk_id: int, task_id: int, score: int) -> bool:
    """Сохраняет количество баллов за выполненное задание"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Добавляем колонку score в user_tasks, если её нет
        c.execute("PRAGMA table_info(user_tasks)")
        columns = [col[1] for col in c.fetchall()]
        if "score" not in columns:
            c.execute("ALTER TABLE user_tasks ADD COLUMN score INTEGER DEFAULT 0")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            """UPDATE user_tasks 
               SET score = ?, completed_date = ?
               WHERE user_vk_id = ? AND task_id = ?""",
            (score, now, user_vk_id, task_id),
        )

        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения баллов: {e}")
        return False
    finally:
        if conn:
            conn.close()


def save_manual_submission(
    user_vk_id: int, task_id: int, submission_url: str, submission_type: str
) -> bool:
    """Сохраняет информацию о ручной отправке работы."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            """INSERT INTO manual_submissions 
                     (user_vk_id, task_id, submission_url, submission_type, submission_date, status)
                     VALUES (?, ?, ?, ?, ?, ?)""",
            (user_vk_id, task_id, submission_url, submission_type, now, "pending"),
        )

        conn.commit()
        print(f"✅ Работа по заданию {task_id} от пользователя {user_vk_id} сохранена")
        return True

    except Exception as e:
        print(f"❌ Ошибка сохранения ручной работы: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Инициализация при импорте модуля
if __name__ != "__main__":
    init_bot_tables()

# Для тестирования
if __name__ == "__main__":
    print("🔧 Тестирование bot_database.py")
    init_bot_tables()
    print(f"📊 Всего пользователей: {len(get_all_users())}")
    # Проверяем получение токена
    token = get_api_token()
    if token:
        print(f"✅ Токен получен: {token[:20]}...")
    else:
        print("❌ Не удалось получить токен")
