import os
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Поддержка двух форматов .env:
# 1) Отдельные переменные: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
# 2) Единая строка: DATABASE_URL (как запасной вариант)
_host = os.getenv("DB_HOST")
_user = os.getenv("DB_USER")
_password = os.getenv("DB_PASSWORD")
_name = os.getenv("DB_NAME")

if _host and _user and _password and _name:
    engine_url = URL.create(
        drivername="postgresql+asyncpg",
        username=_user,
        password=_password,
        host=_host,
        port=5432,
        database=_name,
        query={"ssl": "require"},
    )
else:
    # Запасной вариант — DATABASE_URL
    _raw_url = os.getenv("DATABASE_URL")
    if not _raw_url:
        raise ValueError("Не заданы DB_HOST/DB_USER/DB_PASSWORD/DB_NAME или DATABASE_URL!")
    if _raw_url.startswith("postgresql://"):
        _raw_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine_url = _raw_url

engine = create_async_engine(
    engine_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

INSTITUTES_LIST = [
    "ГИ",
    "ИКНК",
    "ИПМЭиТ",
    "ИСИ",
    "ИБСиБ",
    "ИЭиТ",
    "Физмех",
    "ИЭ",
    "ИММИТ",
    "ИСПО",
]


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
