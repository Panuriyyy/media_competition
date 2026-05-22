import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()


async def check():
    url = os.getenv("DATABASE_URL")
    # Убираем +asyncpg
    clean_url = url.replace("postgresql+asyncpg://", "postgresql://")

    print("Проверка подключения...")

    try:
        conn = await asyncpg.connect(clean_url, ssl="require")
        print("✅ Подключено!")

        # Проверяем версию
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL: {version[:50]}...")

        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(check())
