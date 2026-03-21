from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Task
from passlib.context import CryptContext
from datetime import datetime, timedelta  # Добавлен timedelta
import requests
from typing import List, Dict, Optional
import os

# Конфигурация
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "users.db")
API_URL = "http://127.0.0.1:8001"

# Данные для входа от имени marianna
ADMIN_USERNAME = "marianna"
ADMIN_PASSWORD = "marianna123"

# Хранилище для токена
_token_cache = {"token": None, "expires_at": None}

# Создаем движок SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Хеширование паролей с фиксированной версией bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_api_token() -> Optional[str]:
    """
    Получает токен для доступа к API, логинясь под marianna
    """
    global _token_cache

    # Проверяем, есть ли уже валидный токен
    if _token_cache["token"] and _token_cache["expires_at"]:
        if datetime.now() < _token_cache["expires_at"]:
            return _token_cache["token"]

    try:
        # Логинимся как marianna
        response = requests.post(
            f"{API_URL}/api/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=5,
        )

        if response.ok:
            data = response.json()
            token = data["access_token"]

            # Токен живёт 30 минут (из auth.py), кэшируем на 25 минут
            expires_at = datetime.now() + timedelta(minutes=25)

            _token_cache["token"] = token
            _token_cache["expires_at"] = expires_at

            print(f"✅ Получен токен доступа для {ADMIN_USERNAME}")
            return token
        else:
            print(f"❌ Ошибка получения токена: {response.status_code}")
            if response.status_code == 401:
                print("   Неверные учетные данные для marianna")
            return None

    except requests.exceptions.ConnectionError:
        print(f"❌ Нет подключения к API по адресу {API_URL}")
        return None
    except Exception as e:
        print(f"❌ Ошибка при получении токена: {e}")
        return None


def get_active_tasks_from_api() -> List[Dict]:
    """
    Получает список активных заданий из API сайта с использованием токена
    """
    token = get_api_token()
    if not token:
        print("❌ Нет токена для доступа к API")
        return []

    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.get(f"{API_URL}/api/tasks", headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            tasks = data.get("tasks", [])

            # Фильтруем активные задания
            now = datetime.now()
            active_tasks = []

            for task in tasks:
                if not task.get("is_active", False):
                    continue

                deadline_str = task.get("deadline", "")
                if deadline_str:
                    # Убираем 'Z' если есть
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
            print("❌ Токен истёк или недействителен")
            # Сбрасываем кэш токена
            _token_cache["token"] = None
            _token_cache["expires_at"] = None
            return []
        else:
            print(f"⚠️ API вернул код {response.status_code}")
            return []

    except requests.exceptions.ConnectionError:
        print(f"❌ Нет подключения к API по адресу {API_URL}")
        return []
    except Exception as e:
        print(f"❌ Ошибка при запросе к API: {e}")
        return []


def init_db():
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Проверяем, есть ли уже пользователи
    if db.query(User).count() == 0:
        # Создаем трех пользователей
        users = [
            {
                "username": "marianna",
                "full_name": "Марианна Юрьевна",
                "password": "marianna123",
            },
            {
                "username": "olesya",
                "full_name": "Олеся Игоревна",
                "password": "olesya123",
            },
            {
                "username": "vera",
                "full_name": "Вера Владиславовна",
                "password": "vera123",
            },
        ]

        for user_data in users:
            try:
                password_bytes = user_data["password"].encode("utf-8")[:72]
                hashed_password = pwd_context.hash(password_bytes.decode("utf-8"))

                user = User(
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    password_hash=hashed_password,
                    role="admin",
                )
                db.add(user)
            except Exception as e:
                print(
                    f"❌ Ошибка при создании пользователя {user_data['username']}: {e}"
                )

        try:
            db.commit()
            print("✅ База данных инициализирована с пользователями")
        except Exception as e:
            print(f"❌ Ошибка при сохранении пользователей: {e}")
            db.rollback()
    else:
        print("✅ Пользователи уже существуют в БД")

    db.close()
