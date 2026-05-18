from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# URL базы данных (для локальной разработки - SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./media_contest.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Список институтов для валидации
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
