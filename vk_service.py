import httpx
import re
import os
import json
from typing import List, Optional, Tuple

VK_SERVICE_TOKEN = os.getenv(
    "VK_SERVICE_TOKEN",
    "f87e1ef7f87e1ef7f87e1ef735fb3f1639ff87ef87e1ef79278786d233e1f1e0290460a",
)
VK_API_VERSION = "5.199"


def parse_vk_url(url: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Извлекает owner_id и item_id из ссылки VK.
    Поддерживает форматы:
    - https://vk.com/wall-12345_678
    - https://vk.com/wall12345_678
    - wall-12345_678
    """
    match = re.search(r"wall(-?\d+)_(\d+)", url)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


async def resolve_screen_name(
    screen_name: str, client: httpx.AsyncClient
) -> Optional[str]:
    """
    Преобразует короткое имя пользователя (screen_name) в числовой ID.
    Например: 'durov' -> '1'
    """
    if not screen_name:
        return None

    # Если уже число, возвращаем как есть
    if screen_name.isdigit():
        return screen_name

    # Убираем возможные префиксы
    screen_name = screen_name.strip("/")
    # Если вдруг передали полную ссылку — вытаскиваем только username
    url_match = re.search(r"vk\.(?:com|ru)/([a-zA-Z0-9_.]+)", screen_name)
    if url_match:
        screen_name = url_match.group(1)
    if screen_name.startswith("id"):
        id_match = re.search(r"id(\d+)", screen_name)
        if id_match:
            return id_match.group(1)

    try:
        # Запрос к VK API для получения информации о пользователе
        response = await client.get(
            "https://api.vk.com/method/users.get",
            params={
                "user_ids": screen_name,
                "access_token": VK_SERVICE_TOKEN,
                "v": VK_API_VERSION,
            },
        )
        data = response.json()

        if "error" in data:
            print(f"VK API error in resolve_screen_name: {data['error']}")
            return None

        users = data.get("response", [])
        if users and len(users) > 0:
            user_id = users[0].get("id")
            if user_id:
                return str(user_id)

        return None
    except Exception as e:
        print(f"Error resolving screen name {screen_name}: {e}")
        return None


async def extract_user_id(
    vk_identifier: str, client: httpx.AsyncClient
) -> Optional[str]:
    """
    Извлекает числовой ID пользователя из различных форматов ввода:
    - Числовой ID: '123456'
    - Ссылка: 'https://vk.com/id123456'
    - Ссылка: 'https://vk.com/durov'
    - Короткое имя: 'durov'
    """
    if not vk_identifier:
        return None

    # Очищаем строку
    vk_identifier = vk_identifier.strip()

    # Если это ссылка, извлекаем username или id (поддерживаем vk.com и vk.ru)
    if "vk.com/" in vk_identifier or "vk.ru/" in vk_identifier:
        match = re.search(r"vk\.(?:com|ru)/([a-zA-Z0-9_.]+)", vk_identifier)
        if match:
            username = match.group(1)
            return await resolve_screen_name(username, client)
        return None

    # Если это уже числовой ID
    if vk_identifier.isdigit():
        return vk_identifier

    # Пробуем как короткое имя
    return await resolve_screen_name(vk_identifier, client)


async def check_like(
    client: httpx.AsyncClient, user_id: str, owner_id: int, item_id: int
) -> float:
    """Проверяет лайк через likes.getList (работает с сервисным токеном)"""
    try:
        numeric_user_id = int(user_id)
        offset = 0
        while True:
            response = await client.get(
                "https://api.vk.com/method/likes.getList",
                params={
                    "type": "post",
                    "owner_id": owner_id,
                    "item_id": item_id,
                    "access_token": VK_SERVICE_TOKEN,
                    "v": VK_API_VERSION,
                    "count": 100,
                    "offset": offset,
                    "filter": "likes",
                    "extended": 0,
                },
            )
            data = response.json()

            if "error" in data:
                error_code = data["error"].get("error_code")
                error_msg = data["error"].get("error_msg", "")
                print(f"VK API error in likes.getList (code {error_code}): {error_msg}")
                return 0.0

            resp = data.get("response", {})
            total = resp.get("count", 0)
            items = resp.get("items", [])

            if numeric_user_id in items:
                return 1.0

            offset += len(items)
            if not items or offset >= total or offset >= 1000:
                break

        return 0.0
    except Exception as e:
        print(f"Error checking like for user {user_id}, post {owner_id}_{item_id}: {e}")
        return 0.0


async def check_comment(
    client: httpx.AsyncClient, user_id: str, owner_id: int, item_id: int
) -> float:
    """Проверяет, оставил ли пользователь комментарий под постом"""
    try:
        user_id_str = str(user_id)

        # Сначала получаем количество комментариев, чтобы знать, сколько запрашивать
        count_response = await client.get(
            "https://api.vk.com/method/wall.getComments",
            params={
                "owner_id": owner_id,
                "post_id": item_id,
                "access_token": VK_SERVICE_TOKEN,
                "v": VK_API_VERSION,
                "count": 1,  # Запрашиваем 1 комментарий только для получения общего количества
            },
        )
        count_data = count_response.json()

        if "error" in count_data:
            print(f"VK API error in getComments count: {count_data['error']}")
            return 0.0

        total_comments = count_data.get("response", {}).get("count", 0)

        # Если комментариев нет, сразу возвращаем 0
        if total_comments == 0:
            return 0.0

        # Загружаем комментарии с пагинацией, пока не найдём нужный или не проверим все
        offset = 0
        max_comments_to_check = min(
            total_comments, 500
        )  # Проверяем максимум 500 комментариев

        while offset < max_comments_to_check:
            response = await client.get(
                "https://api.vk.com/method/wall.getComments",
                params={
                    "owner_id": owner_id,
                    "post_id": item_id,
                    "access_token": VK_SERVICE_TOKEN,
                    "v": VK_API_VERSION,
                    "count": 100,
                    "offset": offset,
                    "need_likes": 0,
                    "extended": 0,
                },
            )
            data = response.json()

            if "error" in data:
                print(f"VK API error in getComments: {data['error']}")
                return 0.0

            comments = data.get("response", {}).get("items", [])

            # Проверяем каждый комментарий
            for comment in comments:
                comment_from_id = str(comment.get("from_id", ""))
                # Убираем знак минуса для отрицательных ID (сообщества)
                comment_from_id = comment_from_id.lstrip("-")

                # Сравниваем ID
                if comment_from_id == user_id_str:
                    return 3.0

            offset += 100

        return 0.0
    except Exception as e:
        print(
            f"Error checking comment for user {user_id}, post {owner_id}_{item_id}: {e}"
        )
        return 0.0


async def check_vk_activity(
    vk_identifier: str, posts_urls: List[str], auto_type: str
) -> float:
    """
    Проверяет лайки или комментарии пользователя под списком постов.

    Args:
        vk_identifier: ID пользователя, ссылка или короткое имя
        posts_urls: Список ссылок на посты VK
        auto_type: 'likes' или 'comments'

    Returns:
        Общий балл за выполнение задания
    """
    if not vk_identifier or not posts_urls:
        print(f"Missing data: vk_identifier={vk_identifier}, posts_urls={posts_urls}")
        return 0.0

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Получаем числовой ID пользователя
        user_id = await extract_user_id(vk_identifier, client)

        if not user_id:
            print(f"Could not resolve user ID from: {vk_identifier}")
            return 0.0

        print(f"Resolved user ID: {user_id} from {vk_identifier}")

        total_score = 0.0
        posts_checked = 0

        for url in posts_urls:
            owner_id, item_id = parse_vk_url(url)
            if not owner_id or not item_id:
                print(f"Could not parse post URL: {url}")
                continue

            posts_checked += 1

            if auto_type == "likes":
                score = await check_like(client, user_id, owner_id, item_id)
                total_score += score
                print(f"Post {url}: like={score}")

            elif auto_type == "comments":
                score = await check_comment(client, user_id, owner_id, item_id)
                total_score += score
                print(f"Post {url}: comment={score}")

        print(f"Total score: {total_score} for {posts_checked} posts")
        return total_score
