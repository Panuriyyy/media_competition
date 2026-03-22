from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import os
import logging
from typing import List, Dict
from models import BotUser, UserTask
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты из локальных модулей
from database import get_db, init_db, SessionLocal
from models import User, Task
import schemas
import auth
from datetime import timezone


# Создаем lifespan контекстный менеджер
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, выполняемый при запуске приложения
    logger.info("🚀 Запуск приложения...")
    logger.info("Инициализация базы данных...")
    try:
        init_db()
        logger.info("✅ База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
    yield
    logger.info("👋 Приложение завершает работу...")


# Создаем экземпляр FastAPI с lifespan
app = FastAPI(title="Task Management API", lifespan=lifespan)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы
static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"✅ Статические файлы загружены из {static_dir}")
else:
    logger.warning(f"⚠️ Папка {static_dir} не найдена")


# Корневые маршруты
@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("static/login.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Файл login.html не найден</h1>", status_code=404
        )


@app.get("/index", response_class=HTMLResponse)
async def read_index():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Файл index.html не найден</h1>", status_code=404
        )


# API для входа
@app.post("/api/login", response_model=schemas.TokenResponse)
async def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "created_at": user.created_at,
        },
    }


# API для работы с заданиями
@app.post("/api/tasks", response_model=schemas.TaskResponse)
async def create_task(
    task_data: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    posts_json = json.dumps(task_data.posts) if task_data.posts else None

    try:
        # Валидация данных
        if task_data.task_type not in ["auto", "manual"]:
            raise HTTPException(status_code=400, detail="Неверный тип задания")

        if task_data.task_type == "auto" and task_data.auto_type not in [
            "likes",
            "comments",
        ]:
            raise HTTPException(
                status_code=400,
                detail="Для автоматической проверки укажите тип (лайки/комментарии)",
            )

        deadline_naive = task_data.deadline.replace(tzinfo=None)
        now_naive = datetime.now().replace(tzinfo=None)

        if deadline_naive < now_naive:
            raise HTTPException(status_code=400, detail="Дедлайн должен быть в будущем")

        # Создаем задание
        task = Task(
            title=task_data.title,
            description=task_data.description,
            task_type=task_data.task_type,
            auto_type=task_data.auto_type,
            file_format=task_data.file_format,
            posts=posts_json,
            deadline=task_data.deadline,
            created_by=current_user.id,
            is_active=True,
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        posts_list = []
        if task.posts:
            try:
                posts_list = json.loads(task.posts)
            except:
                posts_list = []

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "auto_type": task.auto_type,
            "file_format": task.file_format,
            "posts": posts_list,
            "deadline": task.deadline,
            "created_at": task.created_at,
            "created_by": task.created_by,
            "is_active": task.is_active,
            "creator_name": current_user.full_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при создании задания: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@app.get("/api/tasks", response_model=schemas.TaskListResponse)
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    task_type: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """Получение списка заданий с фильтрацией"""
    try:
        query = db.query(Task)

        # Применяем фильтры
        if task_type:
            query = query.filter(Task.task_type == task_type)
        if is_active is not None:
            query = query.filter(Task.is_active == is_active)

        # Получаем общее количество
        total = query.count()

        tasks = query.order_by(desc(Task.created_at)).offset(skip).limit(limit).all()

        task_responses = []
        for task in tasks:
            posts_list = []
            if task.posts:
                try:
                    posts_list = json.loads(task.posts)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Ошибка парсинга posts для задания {task.id}: {e}")
                    posts_list = []

            task_dict = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "task_type": task.task_type,
                "auto_type": task.auto_type,
                "file_format": task.file_format,
                "posts": posts_list,
                "deadline": task.deadline,
                "created_at": task.created_at,
                "created_by": task.created_by,
                "is_active": task.is_active,
                "creator_name": task.creator.full_name if task.creator else None,
            }
            task_responses.append(task_dict)

        return {"tasks": task_responses, "total": total}

    except Exception as e:
        logger.error(f"❌ Ошибка при получении заданий: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@app.get("/api/tasks/{task_id}", response_model=schemas.TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """Получение конкретного задания по ID"""
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    # ✅ Парсим posts из JSON
    posts_list = []
    if task.posts:
        try:
            posts_list = json.loads(task.posts)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Ошибка парсинга posts для задания {task.id}: {e}")
            posts_list = []

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "auto_type": task.auto_type,
        "file_format": task.file_format,
        "posts": posts_list,
        "deadline": task.deadline,
        "created_at": task.created_at,
        "created_by": task.created_by,
        "is_active": task.is_active,
        "creator_name": task.creator.full_name if task.creator else None,
    }


@app.put("/api/tasks/{task_id}", response_model=schemas.TaskResponse)
async def update_task(
    task_id: int,
    task_data: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """Обновление задания (только для создателя или админа)"""
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    # Проверяем права (только создатель или админ)
    if task.created_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")

    # Обновляем поля
    task.title = task_data.title
    task.description = task_data.description
    task.task_type = task_data.task_type
    task.auto_type = task_data.auto_type
    task.file_format = task_data.file_format
    task.deadline = task_data.deadline
    task.is_active = task_data.is_active

    task.posts = json.dumps(task_data.posts) if task_data.posts else None

    db.commit()
    db.refresh(task)

    posts_list = []
    if task.posts:
        try:
            posts_list = json.loads(task.posts)
        except:
            posts_list = []

    logger.info(
        f"✅ Задание '{task.title}' обновлено пользователем {current_user.username}"
    )

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "auto_type": task.auto_type,
        "file_format": task.file_format,
        "posts": posts_list,
        "deadline": task.deadline,
        "created_at": task.created_at,
        "created_by": task.created_by,
        "is_active": task.is_active,
        "creator_name": task.creator.full_name if task.creator else None,
    }


@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    # Проверяем права (только создатель или админ)
    if task.created_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет прав на удаление")

    # Мягкое удаление (помечаем как неактивное)
    task.is_active = False
    db.commit()

    logger.info(
        f"✅ Задание '{task.title}' деактивировано пользователем {current_user.username}"
    )

    return {"message": "Задание успешно удалено"}


@app.get("/api/bot-users", response_model=List[Dict])
async def get_bot_users(
    db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    """Получение списка пользователей бота с количеством выполненных заданий"""
    try:
        # Получаем всех пользователей бота
        bot_users = db.query(BotUser).all()

        result = []
        for user in bot_users:
            # Считаем количество выполненных заданий
            completed_tasks = (
                db.query(UserTask)
                .filter(
                    UserTask.user_vk_id == user.vk_id, UserTask.status == "completed"
                )
                .count()
            )

            result.append(
                {
                    "id": user.id,
                    "vk_id": user.vk_id,
                    "name": user.name,
                    "institute": user.institute,
                    "group_num": user.group_num,
                    "reg_date": user.reg_date.isoformat() if user.reg_date else None,
                    "is_active": user.is_active,
                    "completed_tasks": completed_tasks,
                }
            )

        return result
    except Exception as e:
        print(f"Ошибка получения пользователей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# Дополнительные эндпоинты
@app.get("/api/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: User = Depends(auth.get_current_user)):
    return current_user


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Server is running"}


# Для запуска напрямую
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True, log_level="info")
