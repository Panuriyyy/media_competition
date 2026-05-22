from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    SmallInteger,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# ============================================================
# ПОЛЬЗОВАТЕЛИ И АУТЕНТИФИКАЦИЯ
# ============================================================


class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name_user = Column(String(50), nullable=False)
    login_user = Column(String(50), unique=True, nullable=False, index=True)
    email_user = Column(String(50), unique=True, nullable=False)
    password_user = Column(String(255), nullable=False)
    role_user = Column(String(20), default="participant")

    # Связи
    participant = relationship(
        "Participant",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    created_tasks = relationship(
        "Task", back_populates="creator", foreign_keys="Task.id_user"
    )
    submissions = relationship(
        "TasksToParticipant",
        back_populates="user",
        foreign_keys="TasksToParticipant.id_user",
    )
    checks = relationship(
        "CheckTasks", back_populates="checker", foreign_keys="[CheckTasks.id_user]"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )


# ============================================================
# УЧАСТНИКИ (расширенная информация)
# ============================================================


class Participant(Base):
    __tablename__ = "participants"

    id_participant = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_user = Column(
        Integer,
        ForeignKey("users.id_user", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    vk_participant = Column(String(50), nullable=False)
    tg_participant = Column(String(50), nullable=True)
    institute_participant = Column(String(50), nullable=False)

    # Связи - ИСПРАВЛЕНО: убираем submissions отсюда
    user = relationship("User", back_populates="participant")


# ============================================================
# ЗАДАНИЯ
# ============================================================


class Task(Base):
    __tablename__ = "tasks"

    id_tasks = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_user = Column(
        Integer, ForeignKey("users.id_user", ondelete="SET NULL"), nullable=True
    )
    name_tasks = Column(String(200), nullable=False)
    description_tasks = Column(Text, nullable=False)
    type_tasks = Column(SmallInteger, nullable=False, default=1)
    deadline_tasks = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    auto_type = Column(String(20), nullable=True)
    posts_urls = Column(Text, nullable=True)
    points_per_action = Column(Integer, default=1)

    # Связи
    creator = relationship(
        "User", back_populates="created_tasks", foreign_keys=[id_user]
    )
    submissions = relationship(
        "TasksToParticipant", back_populates="task", cascade="all, delete-orphan"
    )
    formats = relationship(
        "FormatFile", back_populates="task", cascade="all, delete-orphan"
    )
    checks = relationship("CheckTasks", back_populates="task")


# ============================================================
# ЗАДАНИЯ УЧАСТНИКОВ (отправленные работы)
# ============================================================


class TasksToParticipant(Base):
    __tablename__ = "tasks_to_participant"

    id_tasks_to_participant = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    id_tasks = Column(
        Integer, ForeignKey("tasks.id_tasks", ondelete="CASCADE"), nullable=False
    )
    id_user = Column(
        Integer, ForeignKey("users.id_user", ondelete="CASCADE"), nullable=False
    )
    date_task_to_participant = Column(DateTime, default=datetime.utcnow, nullable=False)
    url_participant = Column(String(500), nullable=False)
    status = Column(String(20), default="pending")

    # Связи
    task = relationship("Task", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    check = relationship(
        "CheckTasks",
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )


# ============================================================
# ПРОВЕРКА ЗАДАНИЙ (результаты проверки)
# ============================================================


class CheckTasks(Base):
    __tablename__ = "check_tasks"

    id_check_tasks = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_submission = Column(
        Integer,
        ForeignKey("tasks_to_participant.id_tasks_to_participant", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    id_user = Column(
        Integer, ForeignKey("users.id_user", ondelete="CASCADE"), nullable=False
    )
    id_tasks = Column(
        Integer, ForeignKey("tasks.id_tasks", ondelete="CASCADE"), nullable=False
    )
    points_check_tasks = Column(Integer, default=0, nullable=False)
    date_check_tasks = Column(DateTime, default=datetime.utcnow, nullable=False)
    comment = Column(Text, nullable=True)
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id_user", ondelete="SET NULL"), nullable=True
    )

    # Связи
    submission = relationship("TasksToParticipant", back_populates="check")
    checker = relationship("User", back_populates="checks", foreign_keys=[id_user])
    task = relationship("Task", back_populates="checks")


# ============================================================
# ФОРМАТ ФАЙЛА
# ============================================================


class FormatFile(Base):
    __tablename__ = "format_file"

    id_format_file = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_tasks = Column(
        Integer, ForeignKey("tasks.id_tasks", ondelete="CASCADE"), nullable=False
    )
    name_format_file = Column(String(50), nullable=False)

    # Связи
    task = relationship("Task", back_populates="formats")


# ============================================================
# УВЕДОМЛЕНИЯ
# ============================================================


class Notification(Base):
    __tablename__ = "notifications"

    id_notification = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_user = Column(
        Integer, ForeignKey("users.id_user", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="notifications")


# ============================================================
# О КОНКУРСЕ
# ============================================================


class AboutContest(Base):
    __tablename__ = "about_contest"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(
        Integer, ForeignKey("users.id_user", ondelete="SET NULL"), nullable=True
    )


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(
        Integer, ForeignKey("users.id_user", ondelete="SET NULL"), nullable=True
    )

    creator = relationship("User", foreign_keys=[created_by])


# ============================================================
# FAQ
# ============================================================


class FAQ(Base):
    __tablename__ = "faq"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    order_num = Column(Integer, default=0)
    created_by = Column(
        Integer, ForeignKey("users.id_user", ondelete="SET NULL"), nullable=True
    )


# ============================================================
# ИНДЕКСЫ
# ============================================================

Index("idx_tasks_deadline", Task.deadline_tasks)
Index("idx_submissions_status", TasksToParticipant.status)
Index("idx_notifications_user_unread", Notification.id_user, Notification.is_read)
