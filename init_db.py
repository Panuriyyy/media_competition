import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os

# Явно указываем путь к .env файлу
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)


async def init_database():
    from database import Base
    from models import (
        User,
        Participant,
        Task,
        TasksToParticipant,
        CheckTasks,
        FormatFile,
        Notification,
        AboutContest,
        News,
        FAQ,
    )

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ ОШИБКА: DATABASE_URL не найден в .env файле!")
        return

    print(f"✅ DATABASE_URL загружен: {database_url[:80]}...")
    print(f"Подключение к БД...")

    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        # Создаём все таблицы (новые; существующие не трогает)
        await conn.run_sync(Base.metadata.create_all)
        print("\n✅ Все таблицы успешно созданы!")

        # Безопасная миграция: добавляем новую колонку если её ещё нет
        migrations = [
            "ALTER TABLE check_tasks ADD COLUMN IF NOT EXISTS reviewed_by_id INTEGER REFERENCES users(id_user) ON DELETE SET NULL",
        ]
        for sql in migrations:
            try:
                await conn.execute(text(sql))
                print(f"✅ Миграция применена: {sql[:60]}...")
            except Exception as e:
                print(f"⚠️ Миграция пропущена ({e}): {sql[:60]}...")

        # Проверяем, какие таблицы есть
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = result.fetchall()
        print(f"\n📋 Таблицы в БД ({len(tables)}):")
        for table in tables:
            print(f"   - {table[0]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
