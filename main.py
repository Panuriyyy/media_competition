import os
import io
import csv
import json
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    status,
    UploadFile,
    File,
    Form,
    Response,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

# Импорт внутренних модулей проекта
# Убедитесь, что файлы database.py, models.py, auth.py, vk_service.py и schemas.py находятся в той же папке
from database import engine, Base, get_db
from models import User, Task, TaskSubmission, Notification
import auth
import vk_service
import schemas

# Настройка логирования для отслеживания ошибок (поможет при отладке "Parsing body")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация таблиц базы данных
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Медиаконкурс: Профессиональная панель управления",
    description="Система управления заданиями с автоматической проверкой VK API и динамическим расчетом баллов.",
    version="2.0.0",
)

# Настройка CORS (разрешаем фронтенду взаимодействовать с бэкендом)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создание директории для загрузок, если она отсутствует
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ==============================================================================
# ОБРАБОТКА ОШИБОК ВАЛИДАЦИИ (РУСИФИКАЦИЯ И ДЕТАЛИЗАЦИЯ)
# ==============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Перехватывает ошибки Pydantic и возвращает их в понятном виде.
    """
    logger.error(f"Ошибка валидации запроса: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Ошибка в данных запроса. Убедитесь, что все поля заполнены верно.",
            "errors": exc.errors(),
        },
    )


# ==============================================================================
# 1. СИСТЕМА ПОЛЬЗОВАТЕЛЕЙ И АУТЕНТИФИКАЦИЯ
# ==============================================================================


@app.post("/api/register", response_model=schemas.UserOut, tags=["Auth"])
async def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового участника."""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=400, detail="Пользователь с таким логином уже существует."
        )

    new_user = User(
        username=user_data.username,
        password_hash=auth.get_password_hash(user_data.password),
        full_name=user_data.full_name,
        email=user_data.email,
        institute=user_data.institute,
        vk_link=user_data.vk_link,
        tg_link=user_data.tg_link,
        role="user",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/api/login", tags=["Auth"])
async def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """Вход в систему и получение токена."""
    user = auth.authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль.")

    access_token = auth.create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
    }


@app.post("/api/auth/vk", tags=["Auth"])
async def vk_auth_callback(vk_data: schemas.VKAuth, db: Session = Depends(get_db)):
    """Авторизация через VK ID OneTap."""
    info_url = f"https://api.vk.com/method/users.get?user_ids={vk_data.user_id}&access_token={vk_data.access_token}&v=5.199"
    async with httpx.AsyncClient() as client:
        response = await client.get(info_url)
        info = response.json()

    if "error" in info:
        raise HTTPException(status_code=401, detail="Ошибка верификации через VK")

    vk_id = str(vk_data.user_id)
    user = db.query(User).filter(User.vk_id == vk_id).first()

    if not user:
        first_name = info["response"][0].get("first_name", "Участник")
        last_name = info["response"][0].get("last_name", "")
        user = User(
            username=f"vk_{vk_id}",
            full_name=f"{first_name} {last_name}".strip(),
            email=f"vk_{vk_id}@example.com",
            password_hash="vk_oauth_user",
            vk_id=vk_id,
            institute="ГИ",  # По умолчанию
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@app.get("/api/users/me", response_model=schemas.UserOut, tags=["Auth"])
async def get_current_user_profile(current_user: User = Depends(auth.get_current_user)):
    """Получение данных текущего пользователя."""
    return current_user


# ==============================================================================
# 2. УПРАВЛЕНИЕ ЗАДАНИЯМИ (БИЗНЕС-ЛОГИКА)
# ==============================================================================


@app.post("/api/tasks", tags=["Admin/Tasks"])
async def create_task(
    task_data: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """Создание задания. Реализован автоматический расчет баллов для типа 'auto'."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    # ЛОГИКА 1: Автоматический расчет баллов для VK заданий
    points_to_save = task_data.points_at_stake
    if task_data.task_type == "auto":
        num_posts = len(task_data.posts_urls) if task_data.posts_urls else 0
        multiplier = 1 if task_data.auto_type == "likes" else 3
        points_to_save = num_posts * multiplier
        logger.info(
            f"Рассчитаны баллы для авто-задания: {num_posts} постов * {multiplier} = {points_to_save}"
        )

    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        task_type=task_data.task_type,
        auto_type=task_data.auto_type,
        points_at_stake=points_to_save,
        deadline=task_data.deadline,
        posts_urls=json.dumps(task_data.posts_urls) if task_data.posts_urls else None,
        is_active=True,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Уведомление всех пользователей о новом задании
    users = db.query(User).filter(User.role == "user").all()
    for u in users:
        db.add(
            Notification(
                user_id=u.id,
                title="Новое задание!",
                message=f"Опубликовано задание '{new_task.title}'. Баллов на кону: {points_to_save}",
            )
        )
    db.commit()

    return {"message": "Задание успешно создано", "calculated_points": points_to_save}


@app.get(
    "/api/tasks/available", response_model=List[schemas.TaskOut], tags=["User/Tasks"]
)
async def list_available_tasks(
    db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    """Список заданий, доступных пользователю (не просрочены и не выполнены)."""
    now = datetime.utcnow()
    # Получаем ID заданий, которые пользователь уже сдавал
    submitted_ids = [s.task_id for s in current_user.submissions]

    query = db.query(Task).filter(Task.is_active == True, Task.deadline > now)

    if submitted_ids:
        query = query.filter(~Task.id.in_(submitted_ids))

    return query.all()


@app.post("/api/tasks/{task_id}/submit", tags=["User/Tasks"])
async def submit_task_solution(
    task_id: int,
    submission_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """
    Прием решения задачи.
    Включает:
    1. Автопроверку VK (лайки/комменты).
    2. Валидацию форматов файлов (Фото: JPG/PNG, Текст: PDF/DOCX).
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено.")

    # Проверка на повторную сдачу
    existing = (
        db.query(TaskSubmission)
        .filter_by(task_id=task_id, user_id=current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Вы уже сдали это задание.")

    submission = TaskSubmission(task_id=task_id, user_id=current_user.id)

    # ЛОГИКА 2: АВТОМАТИЧЕСКАЯ ПРОВЕРКА (VK API)
    if task.task_type == "auto":
        posts_list = json.loads(task.posts_urls) if task.posts_urls else []
        vk_id = current_user.vk_id or current_user.vk_link  # Идентификатор для поиска

        if not vk_id:
            raise HTTPException(
                status_code=400, detail="В профиле не указан ВК для проверки."
            )

        # Вызов сервиса проверки (лайки/комменты)
        score = await vk_service.check_vk_activity(vk_id, posts_list, task.auto_type)
        submission.score = score
        submission.status = "approved" if score > 0 else "rejected"
        submission.submission_data = "Результат автопроверки VK"

    # ЛОГИКА 3: РУЧНАЯ ПРОВЕРКА С ВАЛИДАЦИЕЙ ФОРМАТОВ
    else:
        submission.status = "pending"
        submission.score = 0

        if file:
            filename = file.filename.lower()
            ext = os.path.splitext(filename)[1]

            # Строгая валидация по типам
            # Проверяем вхождение ключевых слов в описание задания (как метку формата)
            desc_upper = task.description.upper()

            # Валидация для ФОТО
            if "JPG" in desc_upper or "PNG" in desc_upper:
                if ext not in [".jpg", ".jpeg", ".png"]:
                    raise HTTPException(
                        status_code=400, detail="Ошибка: Ожидалось фото (JPG, PNG)."
                    )

            # Валидация для ТЕКСТА
            elif "PDF" in desc_upper or "DOCX" in desc_upper:
                if ext not in [".pdf", ".docx"]:
                    raise HTTPException(
                        status_code=400, detail="Ошибка: Ожидался документ (PDF, DOCX)."
                    )

            # Сохранение файла
            unique_name = f"user_{current_user.id}_task_{task_id}_{datetime.now().timestamp()}{ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)

            try:
                contents = await file.read()
                with open(file_path, "wb") as f:
                    f.write(contents)
                submission.submission_data = f"/uploads/{unique_name}"
            except Exception as e:
                logger.error(f"Ошибка сохранения файла: {e}")
                raise HTTPException(
                    status_code=500, detail="Ошибка при сохранении файла на сервере."
                )

        elif submission_url and submission_url != "auto_check_vk":
            submission.submission_data = submission_url
        else:
            raise HTTPException(
                status_code=400, detail="Необходимо прикрепить файл или указать ссылку."
            )

    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"status": submission.status, "score": submission.score}


# ==============================================================================
# 3. АДМИН-ПАНЕЛЬ: ПРОВЕРКА И УПРАВЛЕНИЕ
# ==============================================================================


@app.get("/api/admin/tasks", tags=["Admin/Tasks"])
async def get_all_tasks_for_admin(
    db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    """Получение всех заданий для управления (включая архивные)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403)
    return db.query(Task).order_by(Task.id.desc()).all()


@app.post("/api/admin/tasks/{task_id}/archive", tags=["Admin/Tasks"])
async def move_task_to_archive(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """Деактивация задания (перенос в архив)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403)
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.is_active = False
        db.commit()
    return {"status": "success", "message": "Задание архивировано"}


@app.get("/api/admin/submissions", tags=["Admin/Reviews"])
async def list_all_submissions(
    db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    """Получение списка всех сданных работ для проверки."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403)

    subs = db.query(TaskSubmission).order_by(TaskSubmission.id.desc()).all()
    results = []
    for s in subs:
        task = db.query(Task).filter(Task.id == s.task_id).first()
        user = db.query(User).filter(User.id == s.user_id).first()
        results.append(
            {
                "id": s.id,
                "task_id": s.task_id,
                "user_id": s.user_id,
                "task_title": task.title if task else "Удаленное задание",
                "user_name": user.full_name if user else "Удаленный пользователь",
                "submission_data": s.submission_data,
                "status": s.status,
                "score": s.score,
                "max_points": task.points_at_stake if task else 0,
            }
        )
    return results


@app.post("/api/submissions/{sub_id}/review", tags=["Admin/Reviews"])
async def review_student_submission(
    sub_id: int,
    status: str = Form(...),
    score: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """Выставление оценки и статуса работе (динамический ввод баллов)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403)

    sub = db.query(TaskSubmission).filter(TaskSubmission.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Работа не найдена.")

    # Валидация баллов (нельзя поставить больше максимума)
    if score > sub.task.points_at_stake:
        raise HTTPException(
            status_code=400,
            detail=f"Оценка не может превышать {sub.task.points_at_stake}",
        )

    sub.status = status
    sub.score = score

    # Уведомление студенту о проверке
    db.add(
        Notification(
            user_id=sub.user_id,
            title="Работа проверена",
            message=f"Задание '{sub.task.title}' проверено. Оценка: {score}",
        )
    )
    db.commit()
    return {"message": "Оценка успешно сохранена"}


# ==============================================================================
# 4. АНАЛИТИКА И ОТЧЕТНОСТЬ
# ==============================================================================


@app.get("/api/stats/dashboard", tags=["Admin/Stats"])
async def get_dashboard_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    """Сводные данные для главной страницы админа."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403)

    total_u = db.query(User).filter(User.role == "user").count()

    # Статистика по институтам
    inst_stats = (
        db.query(User.institute, func.count(User.id))
        .filter(User.role == "user")
        .group_by(User.institute)
        .all()
    )

    return {
        "total_users": total_u,
        "institutes_activity": [{"institute": i, "count": c} for i, c in inst_stats],
    }


@app.get("/api/reports/csv", tags=["Admin/Stats"])
async def export_rating_to_csv(db: Session = Depends(get_db)):
    """Выгрузка общего рейтинга в формате CSV."""
    users = db.query(User).filter(User.role == "user").all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ФИО", "Институт", "Суммарный балл"])

    for u in users:
        total_score = (
            db.query(func.sum(TaskSubmission.score))
            .filter(TaskSubmission.user_id == u.id)
            .scalar()
            or 0
        )
        writer.writerow([u.full_name, u.institute, total_score])

    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rating_media.csv"},
    )


@app.get("/api/reports/txt", tags=["Admin/Stats"])
async def export_rating_to_txt(db: Session = Depends(get_db)):
    """Выгрузка рейтинга в текстовый файл."""
    users = db.query(User).filter(User.role == "user").all()
    lines = ["РЕЙТИНГ УЧАСТНИКОВ МЕДИАКОНКУРСА\n", "=" * 30 + "\n"]

    for u in users:
        score = (
            db.query(func.sum(TaskSubmission.score))
            .filter(TaskSubmission.user_id == u.id)
            .scalar()
            or 0
        )
        lines.append(f"{u.full_name} ({u.institute}) — {score} баллов\n")

    return PlainTextResponse(
        "".join(lines),
        headers={"Content-Disposition": "attachment; filename=rating_media.txt"},
    )


# ==============================================================================
# 5. СИСТЕМА УВЕДОМЛЕНИЙ
# ==============================================================================


@app.get("/api/users/me/notifications", tags=["User/Notifs"])
async def get_my_notifications(
    db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    """Получение списка уведомлений пользователя."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.id.desc())
        .all()
    )


@app.post("/api/notifications/{n_id}/read", tags=["User/Notifs"])
async def mark_notification_as_read(n_id: int, db: Session = Depends(get_db)):
    """Отметка уведомления как прочитанного."""
    n = db.query(Notification).filter(Notification.id == n_id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"status": "ok"}


# ==============================================================================
# 6. МОНТИРОВАНИЕ СТАТИКИ И ЗАПУСК
# ==============================================================================

# Раздача загруженных файлов
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# Раздача фронтенда (HTML/JS/CSS) из корня проекта
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    # Запуск на порту 8001
    uvicorn.run(app, host="127.0.0.1", port=8001)
