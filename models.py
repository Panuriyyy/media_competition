from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    Float,
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="user")  # admin / user
    institute = Column(String)  # Для дашборда по институтам
    vk_id = Column(String, nullable=True)  # Для авторизации и проверки лайков
    vk_link = Column(String, nullable=True)
    tg_link = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("TaskSubmission", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    task_type = Column(String, nullable=False)  # auto / manual
    auto_type = Column(String, nullable=True)  # likes / comments
    points_at_stake = Column(Float, default=0)
    deadline = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    posts_urls = Column(Text, nullable=True)  # JSON-строка со ссылками на посты VK
    created_at = Column(DateTime, default=datetime.utcnow)


class TaskSubmission(Base):
    __tablename__ = "task_submissions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    submission_data = Column(Text)  # Ссылка или путь к загруженному файлу
    status = Column(String, default="pending")  # pending, approved, rejected
    score = Column(Float, default=0)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="submissions")
    task = relationship("Task")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
