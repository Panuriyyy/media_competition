from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.now)

    # Связь с заданиями
    tasks = relationship("Task", back_populates="creator")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    task_type = Column(String, nullable=False)
    auto_type = Column(String, nullable=True)
    file_format = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)

    # Связь с создателем
    creator = relationship("User", back_populates="tasks")


class BotUser(Base):
    __tablename__ = "bot_users"

    id = Column(Integer, primary_key=True, index=True)
    vk_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    institute = Column(String)
    group_num = Column(String)
    reg_date = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    # Связь с отправленными уведомлениями
    notifications = relationship("SentNotification", back_populates="user")
    # Связь с выполненными заданиями
    completed_tasks = relationship("UserTask", back_populates="user")


class SentNotification(Base):
    __tablename__ = "sent_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_vk_id = Column(Integer, ForeignKey("bot_users.vk_id"))
    task_id = Column(Integer, nullable=False)
    sent_date = Column(DateTime, default=datetime.now)

    # Связь с пользователем
    user = relationship("BotUser", back_populates="notifications")

    __table_args__ = (
        UniqueConstraint("user_vk_id", "task_id", name="unique_user_task_notification"),
    )


class UserTask(Base):
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_vk_id = Column(Integer, ForeignKey("bot_users.vk_id"), nullable=False)
    task_id = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # 'pending', 'completed', 'failed'
    completed_date = Column(DateTime, nullable=True)

    user = relationship("BotUser", back_populates="completed_tasks")

    __table_args__ = (
        UniqueConstraint("user_vk_id", "task_id", name="unique_user_task_completion"),
    )


class ManualSubmission(Base):
    __tablename__ = "manual_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_vk_id = Column(Integer, ForeignKey("bot_users.vk_id"), nullable=False)
    task_id = Column(Integer, nullable=False)
    submission_url = Column(String)
    submission_type = Column(String)  # 'photo', 'doc', 'video', 'audio', 'link'
    submission_date = Column(DateTime, default=datetime.now)
    status = Column(String, default="pending")  # 'pending', 'approved', 'rejected'

    # Связь с пользователем
    user = relationship("BotUser")
