import os
import re
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

_raw_url = os.getenv("DATABASE_URL")

if not _raw_url:
    raise ValueError("DATABASE_URL не задан в файле .env!")

# Парсим URL вручную через regex — надёжно работает с любыми спецсимволами в пароле
_match = re.match(
    r"^(?:postgresql(?:\+asyncpg)?://)"
    r"(?P<user>[^:]+):(?P<password>.+)@"
    r"(?P<host>[^/:]+)(?::(?P<port>\d+))?/(?P<db>[^?]+)",
    _raw_url,
)

if not _match:
    raise ValueError("Неверный формат DATABASE_URL!")

# Строим URL через SQLAlchemy — он сам корректно кодирует пароль
engine_url = URL.create(
    drivername="postgresql+asyncpg",
    username=_match.group("user"),
    password=_match.group("password"),
    host=_match.group("host"),
    port=int(_match.group("port")) if _match.group("port") else 5432,
    database=_match.group("db"),
    query={"ssl": "require"},
)

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
