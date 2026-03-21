from vkbottle.bot import Bot, Message
from vkbottle import (
    Keyboard,
    KeyboardButtonColor,
    Text,
    EMPTY_KEYBOARD,
)
from config import (
    VK_TOKEN,
    GROUP_ID,
    GROUP_SCREEN_NAME,
    API_URL,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
)
from vkbottle import BaseStateGroup
from vkbottle import CtxStorage
import re
import asyncio
from datetime import datetime
import requests
import os
from typing import List, Dict, Optional
import logging

from bot_database import (
    init_bot_tables,
    save_user,
    get_all_users,
    get_active_tasks_from_api,
    has_received_notification,
    mark_notification_sent,
    get_user_info,
    save_user_task_completion,
    get_user_task_status,
    save_manual_submission,
)

init_bot_tables()

bot = Bot(token=VK_TOKEN)

ctx = CtxStorage()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ID группы ВКонтакте
GROUP_ID = 234420247
GROUP_SCREEN_NAME = "polytech_petra"


class RegData(BaseStateGroup):
    NAME = 0
    INSTITUTE = 1


def is_russian_text(text: str) -> bool:
    return bool(re.match(r"^[а-яА-ЯёЁ\s\-]+$", text))


def to_lower_text(text: str) -> str:
    return text.lower()


def extract_post_id_from_url(url: str) -> Optional[int]:
    """Извлекает ID поста из ссылки вида https://vk.com/wall-123456_789"""
    try:
        if "wall" in url:
            wall_part = url.split("wall")[-1]
            post_id = wall_part.split("_")[-1]
            return int(post_id)
    except:
        pass
    return None


async def check_user_likes(user_id: int, post_ids: List[int], owner_id: int) -> bool:
    """Проверяет, лайкнул ли пользователь указанные посты"""
    try:
        for post_id in post_ids:
            response = requests.get(
                "https://api.vk.com/method/likes.isLiked",
                params={
                    "user_id": user_id,
                    "type": "post",
                    "owner_id": owner_id,
                    "item_id": post_id,
                    "access_token": bot.token,
                    "v": "5.131",
                },
            )
            if response.ok:
                if response.json().get("response", {}).get("liked") != 1:
                    return False
            else:
                return False
        return True
    except Exception as e:
        logger.error(f"Ошибка проверки лайков: {e}")
        return False


async def check_user_comments(user_id: int, post_ids: List[int], owner_id: int) -> bool:
    """Проверяет, оставил ли пользователь комментарии под указанными постами"""
    try:
        for post_id in post_ids:
            response = requests.get(
                "https://api.vk.com/method/wall.getComments",
                params={
                    "owner_id": owner_id,
                    "post_id": post_id,
                    "count": 100,
                    "access_token": bot.token,
                    "v": "5.131",
                },
            )
            if response.ok:
                comments = response.json().get("response", {}).get("items", [])
                if not any(c.get("from_id") == user_id for c in comments):
                    return False
            else:
                return False
        return True
    except Exception as e:
        logger.error(f"Ошибка проверки комментариев: {e}")
        return False


def validate_file_extension(filename: str, allowed_formats: str) -> bool:
    """Проверяет расширение файла на соответствие разрешенным форматам"""
    if not filename or not allowed_formats:
        return False

    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    allowed = [fmt.strip().lower() for fmt in allowed_formats.replace(",", " ").split()]
    return ext in allowed


# ==================== 1. КОНКРЕТНЫЕ ТЕКСТОВЫЕ КОМАНДЫ ====================


@bot.on.private_message(text=["начать", "Начать", "НАЧАТЬ"])
async def start_handler(message: Message):
    """Начало диалога"""
    logger.info(f"Пользователь {message.from_id}: начало диалога")

    # Проверяем, зарегистрирован ли пользователь
    user_info = get_user_info(message.from_id)
    if user_info:
        await message.answer("С возвращением!", keyboard=EMPTY_KEYBOARD)
        await show_available_tasks(message)
        return

    keyboard = Keyboard()
    keyboard.add(Text("Да, участвую в конкурсе"), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("Нет, другой вопрос"), color=KeyboardButtonColor.SECONDARY)

    await message.answer(
        "Собираетесь ли вы принять участие в конкурсе медиаактивности?",
        keyboard=keyboard,
    )


@bot.on.private_message(text="Да, участвую в конкурсе")
async def competition_handler(message: Message):
    """Согласие на участие"""
    logger.info(f"Пользователь {message.from_id}: согласие на участие")

    await message.answer(
        "Ура! Нас ждёт погружение в среду медиа Политеха. Ознакомься с правилами:\n\n"
        "1. Правило первое\n2. Правило второе\n3. Правило третье",
        keyboard=EMPTY_KEYBOARD,
    )

    keyboard = Keyboard()
    keyboard.add(Text("Да, прочитал"), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("Нет"), color=KeyboardButtonColor.NEGATIVE)

    await message.answer("Ознакомились ли вы с правилами?", keyboard=keyboard)


@bot.on.private_message(text="Да, прочитал")
async def reg_handler(message: Message):
    """Начало регистрации"""
    logger.info(f"Пользователь {message.from_id}: начало регистрации")

    await bot.state_dispenser.set(message.peer_id, RegData.NAME)
    await message.answer("Введите ваше ФИО. Например: Иванов Иван Иванович")


@bot.on.private_message(text="ПОДТВЕРДИТЬ РЕГИСТРАЦИЮ")
async def confirm_handler(message: Message):
    """Подтверждение регистрации"""
    logger.info(f"Пользователь {message.from_id}: подтверждение регистрации")

    # Получаем данные из контекста
    name = ctx.get("name")
    institute = ctx.get("institute")

    if not name or not institute:
        await message.answer(
            "❌ Данные не найдены. Начните заново: Начать", keyboard=EMPTY_KEYBOARD
        )
        return

    # Завершаем состояние
    await bot.state_dispenser.delete(message.peer_id)

    # Сохраняем в БД
    save_user(message.from_id, name, institute, "")

    # Очищаем контекст
    ctx.delete("name")
    ctx.delete("institute")

    await message.answer("✅ Регистрация успешно завершена!", keyboard=EMPTY_KEYBOARD)

    await show_available_tasks(message)


@bot.on.private_message(text="Начать заново")
async def restart_handler(message: Message):
    """Сброс регистрации"""
    logger.info(f"Пользователь {message.from_id}: сброс регистрации")

    # Очищаем контекст
    ctx.delete("name")
    ctx.delete("institute")

    # Устанавливаем состояние на начало
    await bot.state_dispenser.set(message.peer_id, RegData.NAME)
    await message.answer("Введите ваше ФИО:", keyboard=EMPTY_KEYBOARD)


@bot.on.private_message(text="Посмотреть задания")
async def show_tasks_handler(message: Message):
    """Показать задания"""
    await show_available_tasks(message)


@bot.on.private_message(text="Да, приступить")
async def start_task_now_handler(message: Message):
    """Начать выполнение"""
    task = ctx.get(f"current_task_{message.from_id}")

    if not task:
        await message.answer("Задание не выбрано", keyboard=EMPTY_KEYBOARD)
        return

    if task["task_type"] == "auto":
        await handle_auto_task(message, task)
    else:
        await handle_manual_task(message, task)


@bot.on.private_message(text="Позже")
async def start_task_later_handler(message: Message):
    """Отложить выполнение"""
    await message.answer(
        "Хорошо! Вы всегда можете вернуться через 'Посмотреть задания'",
        keyboard=EMPTY_KEYBOARD,
    )
    await show_available_tasks(message)


@bot.on.private_message(text="Нет, другой вопрос")
async def others_handler(message: Message):
    """Другие вопросы"""
    await message.answer(
        "Если есть вопросы, напишите их. Мы ответим!", keyboard=EMPTY_KEYBOARD
    )
    try:
        await bot.api.messages.mark_as_important_conversation(
            peer_id=message.peer_id, important=1
        )
    except Exception as e:
        logger.error(f"Ошибка пометки важным: {e}")


@bot.on.private_message(text="Нет")
async def rules_decline_handler(message: Message):
    """Отказ от правил"""
    keyboard = Keyboard().add(
        Text("Ознакомиться с правилами", payload={"cmd": "rules"})
    )
    await message.answer(
        "Нужно ознакомиться с правилами для участия", keyboard=keyboard
    )


# ==================== 2. ОБРАБОТЧИКИ С PAYLOAD ====================


@bot.on.private_message(payload_contains={"action": "offer_task"})
async def offer_task_handler(message: Message):
    """Предложение выполнить задание"""
    payload = message.get_payload_json()
    task_id = payload.get("task_id")

    tasks = get_active_tasks_from_api()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        await message.answer("Задание не найдено", keyboard=EMPTY_KEYBOARD)
        return

    ctx.set(f"current_task_{message.from_id}", task)

    keyboard = Keyboard()
    keyboard.add(Text("Да, приступить"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("Позже"), color=KeyboardButtonColor.SECONDARY)

    await message.answer(
        f"**{task['title']}**\n\n{task['description']}\n\nПриступить?",
        keyboard=keyboard,
    )


@bot.on.private_message(payload_contains={"action": "retry_auto"})
async def retry_auto_task_handler(message: Message):
    """Повторная проверка автоматического задания"""
    payload = message.get_payload_json()
    task_id = payload.get("task_id")

    tasks = get_active_tasks_from_api()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if task:
        ctx.set(f"current_task_{message.from_id}", task)
        await handle_auto_task(message, task)


# ==================== 3. ОБРАБОТЧИКИ СОСТОЯНИЙ ====================


@bot.on.message(state=RegData.NAME)
async def name_handler(message: Message):
    """Обработка ФИО"""
    text = to_lower_text(message.text)

    if not is_russian_text(text):
        return "Пожалуйста, введите ФИО на русском языке. Пример: иванов иван иванович"

    ctx.set("name", message.text)
    logger.info(f"Пользователь {message.from_id}: ввел имя {message.text}")

    await bot.state_dispenser.set(message.peer_id, RegData.INSTITUTE)
    return "Введите ваш институт. Например: ИКНК, ИПМЭИТ, ГИ"


@bot.on.message(state=RegData.INSTITUTE)
async def institute_handler(message: Message):
    """Обработка института"""
    # Пропускаем команды, которые уже обработаны выше
    if message.text in [
        "ПОДТВЕРДИТЬ РЕГИСТРАЦИЮ",
        "Начать заново",
        "Посмотреть задания",
    ]:
        return

    text = to_lower_text(message.text)

    if not is_russian_text(text):
        return "Пожалуйста, введите название института на русском языке"

    ctx.set("institute", message.text)
    logger.info(f"Пользователь {message.from_id}: ввел институт {message.text}")

    # Получаем данные
    name = ctx.get("name")
    institute = ctx.get("institute")

    # Показываем данные для подтверждения
    await message.answer(
        f"Проверьте данные:\n\n" f"ФИО: {name}\n" f"Институт: {institute}",
        keyboard=EMPTY_KEYBOARD,
    )

    # Создаем клавиатуру для подтверждения
    keyboard = Keyboard()
    keyboard.add(Text("ПОДТВЕРДИТЬ РЕГИСТРАЦИЮ"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("Начать заново"), color=KeyboardButtonColor.SECONDARY)

    await message.answer("Всё правильно?", keyboard=keyboard)


# ==================== 4. ВСЕ ОСТАЛЬНЫЕ СООБЩЕНИЯ ====================


@bot.on.private_message()
async def other_messages(message: Message):
    """Все остальные сообщения"""
    text = to_lower_text(message.text)

    ignored = [
        "начать",
        "да, участвую в конкурсе",
        "нет, другой вопрос",
        "да, прочитал",
        "нет",
        "подтвердить регистрацию",
        "начать заново",
        "посмотреть задания",
        "да, приступить",
        "позже",
    ]

    if text in ignored:
        return

    await message.answer("Я вас не понимаю. Напишите «Начать»", keyboard=EMPTY_KEYBOARD)


# ==================== ФУНКЦИИ ДЛЯ ЗАДАНИЙ ====================


async def show_available_tasks(message: Message):
    """Показывает доступные задания"""
    tasks = get_active_tasks_from_api()

    if not tasks:
        await message.answer(
            "На данный момент нет активных заданий. "
            "Мы сообщим, как только появятся новые!",
            keyboard=EMPTY_KEYBOARD,
        )
        return

    await message.answer(f"Доступно заданий: {len(tasks)}", keyboard=EMPTY_KEYBOARD)

    for task in tasks:
        status = get_user_task_status(message.from_id, task["id"])
        status_text = {"completed": "✅ выполнено", "pending": "⏳ на проверке"}.get(
            status, ""
        )

        keyboard = Keyboard(inline=True)
        keyboard.add(
            Text("Выполнить", payload={"task_id": task["id"], "action": "offer_task"}),
            color=KeyboardButtonColor.POSITIVE,
        )

        await message.answer(
            f"**{task['title']}** {status_text}\n\n"
            f"{task['description']}\n\n"
            f"Дедлайн: {task['deadline'][:16].replace('T', ' ')}\n"
            f"Тип: {'Автоматическая' if task['task_type'] == 'auto' else 'Ручная'}",
            keyboard=keyboard,
        )


async def handle_auto_task(message: Message, task: Dict):
    """Автоматическое задание с проверкой по ссылкам из задания"""
    user_id = message.from_id
    task_id = task["id"]

    # Получаем ссылки на посты из задания (если есть)
    post_links = task.get("posts", [])

    if not post_links:
        await message.answer(
            "В задании не указаны ссылки на посты.", keyboard=EMPTY_KEYBOARD
        )
        return

    # Извлекаем ID постов из ссылок
    post_ids = []
    owner_id = None

    for link in post_links:
        post_id = extract_post_id_from_url(link)
        if post_id:
            post_ids.append(post_id)
            if not owner_id and "-wall" in link:
                owner_part = link.split("-wall")[0].split("/")[-1]
                try:
                    owner_id = -int(owner_part) if owner_part.isdigit() else None
                except:
                    owner_id = None

    if not post_ids:
        await message.answer(
            "Не удалось распознать ссылки на посты.", keyboard=EMPTY_KEYBOARD
        )
        return

    if not owner_id:
        owner_id = -GROUP_ID

    # Проверяем выполнение
    if task.get("auto_type") == "likes":
        completed = await check_user_likes(user_id, post_ids, owner_id)
        check_text = f"лайкнули все {len(post_ids)} постов"
        action_text = "лайк"
    else:
        completed = await check_user_comments(user_id, post_ids, owner_id)
        check_text = f"оставили комментарии под всеми {len(post_ids)} постами"
        action_text = "комментарий"

    if completed:
        save_user_task_completion(user_id, task_id, "completed")
        await message.answer(
            f"✅ Задание выполнено! Вы {check_text}.", keyboard=EMPTY_KEYBOARD
        )
        await show_available_tasks(message)
    else:
        links_text = "\n".join([f"• {link}" for link in post_links])

        keyboard = Keyboard(inline=True)
        keyboard.add(
            Text(
                "🔄 Проверить ещё раз",
                payload={"task_id": task_id, "action": "retry_auto"},
            ),
            color=KeyboardButtonColor.PRIMARY,
        )

        await message.answer(
            f"❌ Задание не выполнено.\n\n"
            f"Вам нужно поставить {action_text} под следующими постами:\n\n"
            f"{links_text}\n\n"
            f"После этого нажмите кнопку ниже.",
            keyboard=keyboard,
        )


async def handle_manual_task(message: Message, task: Dict):
    """Ручное задание с проверкой формата файла"""
    file_format = task.get("file_format", "")

    format_descriptions = {
        "PNG, JPG": "изображения (PNG, JPG)",
        "MOV, MP3, MP4": "видео или аудио (MOV, MP3, MP4)",
        "DOC, DOCS, PDF, TXT": "документы (DOC, DOCS, PDF, TXT)",
    }
    format_desc = format_descriptions.get(file_format, file_format)

    await message.answer(
        f"**{task['title']}**\n\n"
        f"{task['description']}\n\n"
        f"📎 Требуемый формат: {format_desc}\n\n"
        f"Пришлите ссылку или прикрепите файл:",
        keyboard=EMPTY_KEYBOARD,
    )

    ctx.set(f"awaiting_submission_{message.from_id}", task)


@bot.on.message()
async def handle_submission(message: Message):
    """Обработка отправленных файлов"""
    user_id = message.from_id
    task = ctx.get(f"awaiting_submission_{user_id}")

    if not task:
        return

    task_id = task["id"]
    file_format = task.get("file_format", "")

    has_attachment = bool(message.attachments)
    has_link = any(
        x in message.text.lower() for x in ["http://", "https://", "vk.com/"]
    )

    if has_attachment or has_link:
        submission_type = "unknown"
        submission_url = ""
        filename = ""
        valid_format = False

        if message.attachments:
            att = message.attachments[0]
            if att.photo:
                submission_type = "photo"
                submission_url = att.photo.sizes[-1].url
                filename = f"photo_{att.photo.id}.jpg"
                valid_format = (
                    not file_format
                    or "jpg" in file_format.lower()
                    or "png" in file_format.lower()
                )
            elif att.doc:
                submission_type = "doc"
                submission_url = att.doc.url
                filename = att.doc.title
                valid_format = (
                    validate_file_extension(filename, file_format)
                    if file_format
                    else True
                )
            elif att.video:
                submission_type = "video"
                submission_url = (
                    f"https://vk.com/video{att.video.owner_id}_{att.video.id}"
                )
                valid_format = "mp4" in file_format.lower() if file_format else True
            elif att.audio:
                submission_type = "audio"
                submission_url = (
                    f"https://vk.com/audio{att.audio.owner_id}_{att.audio.id}"
                )
                valid_format = "mp3" in file_format.lower() if file_format else True
        else:
            submission_type = "link"
            submission_url = message.text
            valid_format = True

        if not valid_format:
            await message.answer(
                f"❌ Неверный формат.\nТребуется: {file_format}",
                keyboard=EMPTY_KEYBOARD,
            )
            return

        save_manual_submission(user_id, task_id, submission_url, submission_type)

        await message.answer(
            "✅ Работа отправлена на проверку!",
            keyboard=EMPTY_KEYBOARD,
        )

        ctx.delete(f"awaiting_submission_{user_id}")
        await show_available_tasks(message)
    else:
        await message.answer(
            f"❌ Пришлите ссылку или файл.\nТребуемый формат: {file_format}",
            keyboard=EMPTY_KEYBOARD,
        )


# ==================== ФОНОВАЯ ЗАДАЧА ====================


async def check_new_tasks_background():
    """Фоновая проверка новых заданий"""
    sent_tasks = set()

    while True:
        try:
            tasks = get_active_tasks_from_api()
            if tasks:
                users = get_all_users()
                for task in tasks:
                    if task["id"] not in sent_tasks:
                        for user_id in users:
                            if not has_received_notification(user_id, task["id"]):
                                try:
                                    keyboard = Keyboard().add(
                                        Text("Посмотреть задания")
                                    )
                                    await bot.api.messages.send(
                                        peer_id=user_id,
                                        message=f"НОВОЕ ЗАДАНИЕ!\n\n{task['title']}\n{task['description']}\nДедлайн: {task['deadline'][:16].replace('T', ' ')}",
                                        keyboard=keyboard,
                                        random_id=0,
                                    )
                                    mark_notification_sent(user_id, task["id"])
                                    await asyncio.sleep(0.3)
                                except Exception as e:
                                    logger.error(f"Ошибка отправки: {e}")
                        sent_tasks.add(task["id"])
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        await asyncio.sleep(30)


if __name__ == "__main__":
    logger.info("🚀 Запуск бота...")

    import threading

    threading.Thread(
        target=lambda: asyncio.run(check_new_tasks_background()), daemon=True
    ).start()

    bot.run_forever()
