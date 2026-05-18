import asyncio
from datetime import datetime, timedelta
from database import SessionLocal
from models import Task, Notification, User, TaskSubmission


async def check_deadlines_and_notify():
    """Фоновая задача: проверка дедлайнов и отправка уведомлений"""
    while True:
        try:
            db = SessionLocal()
            now = datetime.now()
            tomorrow = now + timedelta(days=1)

            # Задания, у которых дедлайн через 1 день
            tasks_soon = (
                db.query(Task)
                .filter(Task.is_active == True, Task.deadline.between(now, tomorrow))
                .all()
            )

            for task in tasks_soon:
                # Получаем пользователей, которые ещё не выполнили это задание
                users = db.query(User).filter(User.role == "user").all()
                for user in users:
                    existing = (
                        db.query(TaskSubmission)
                        .filter(
                            TaskSubmission.task_id == task.id,
                            TaskSubmission.user_id == user.id,
                        )
                        .first()
                    )

                    if not existing:
                        notification = Notification(
                            user_id=user.id,
                            title="⚠️ Дедлайн приближается!",
                            message=f"До окончания задания '{task.title}' остался 1 день!",
                            is_read=False,
                        )
                        db.add(notification)

            db.commit()
            db.close()

        except Exception as e:
            print(f"Ошибка в фоновой задаче: {e}")

        # Проверяем каждые 6 часов
        await asyncio.sleep(21600)
