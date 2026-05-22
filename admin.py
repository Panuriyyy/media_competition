"""
Создание администратора.

Использование:
    python admin.py                          # логин marianna, пароль marianna123
    python admin.py <логин> <пароль>         # свои данные
    python admin.py <логин> <пароль> <email> # + email
"""

import asyncio
import sys
import os
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

# Явно указываем путь к .env рядом с этим файлом
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


async def create_admin(login: str, password: str, email: str, name: str):
    from models import User, Participant

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ОШИБКА: DATABASE_URL не найден в .env!")
        print(f"Искал файл: {_env_path}")
        return

    print("Подключение к БД...")
    engine = create_async_engine(database_url)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with Session() as session:
            # Проверяем, есть ли уже такой пользователь
            result = await session.execute(
                select(User).where(User.login_user == login)
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"Пользователь '{login}' уже существует (роль: {existing.role_user})")
                if existing.role_user != "admin":
                    existing.role_user = "admin"
                    await session.commit()
                    print("Роль обновлена на 'admin'!")
                else:
                    print("Уже является администратором — ничего не изменено.")
                return

            # Создаём администратора
            print(f"Создаю администратора '{login}'...")

            admin = User(
                name_user=name,
                login_user=login,
                email_user=email,
                password_user=hash_password(password),
                role_user="admin",
            )
            session.add(admin)
            await session.flush()

            participant = Participant(
                id_user=admin.id_user,
                vk_participant="https://vk.com/id0",
                tg_participant="",
                institute_participant="ГИ",
            )
            session.add(participant)
            await session.commit()

            print("\n" + "=" * 50)
            print("АДМИНИСТРАТОР УСПЕШНО СОЗДАН!")
            print("=" * 50)
            print(f"   Логин:  {login}")
            print(f"   Пароль: {password}")
            print(f"   Email:  {email}")
            print("=" * 50)

    except Exception as e:
        print(f"Ошибка: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 0:
        _login    = "marianna"
        _password = "marianna123"
        _email    = "marianna@spbstu.ru"
        _name     = "Администратор"
    elif len(args) == 2:
        _login, _password = args
        _email = f"{_login}@spbstu.ru"
        _name  = _login.capitalize()
    elif len(args) >= 3:
        _login, _password, _email = args[0], args[1], args[2]
        _name = args[3] if len(args) > 3 else _login.capitalize()
    else:
        print("Использование: python admin.py [логин пароль [email [имя]]]")
        sys.exit(1)

    asyncio.run(create_admin(_login, _password, _email, _name))
