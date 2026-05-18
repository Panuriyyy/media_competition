import httpx
import re
import os
import json
from typing import List

# Токены берем из окружения сервера
VK_SERVICE_TOKEN = os.getenv(
    "VK_SERVICE_TOKEN",
    "f87e1ef7f87e1ef7f87e1ef735fb3f1639ff87ef87e1ef79278786d233e1f1e0290460a",
)
VK_API_VERSION = "5.199"


def parse_vk_url(url: str):
    """
    Вытаскивает из ссылки вида https://vk.com/wall-12345_678
    owner_id (-12345) и item_id (678).
    """
    match = re.search(r"wall(-?\d+)_(\d+)", url)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


async def check_vk_activity(vk_id: str, posts_urls_json: str, auto_type: str) -> float:
    """
    Проверяет лайки или комментарии пользователя под списком постов.
    Возвращает итоговый балл: 1 балл за каждый лайк, 3 балла за каждый коммент.
    """
    if not vk_id or not posts_urls_json:
        return 0.0

    try:
        posts_urls: List[str] = json.loads(posts_urls_json)
    except:
        return 0.0

    total_score = 0.0

    async with httpx.AsyncClient() as client:
        for url in posts_urls:
            owner_id, item_id = parse_vk_url(url)
            if not owner_id or not item_id:
                continue

            if auto_type == "likes":
                # Запрос к методу likes.isLiked
                response = await client.get(
                    "https://api.vk.com/method/likes.isLiked",
                    params={
                        "user_id": vk_id,
                        "type": "post",
                        "owner_id": owner_id,
                        "item_id": item_id,
                        "access_token": VK_SERVICE_TOKEN,
                        "v": VK_API_VERSION,
                    },
                )
                data = response.json()
                if data.get("response", {}).get("liked") == 1:
                    total_score += 1.0  # 1 балл за лайк

            elif auto_type == "comments":
                # Запрос к методу wall.getComments (ищем коммент от пользователя)
                response = await client.get(
                    "https://api.vk.com/method/wall.getComments",
                    params={
                        "owner_id": owner_id,
                        "post_id": item_id,
                        "access_token": VK_SERVICE_TOKEN,
                        "v": VK_API_VERSION,
                        "count": 100,  # Проверяем последние 100 комментариев (можно увеличить через offset, если нужно)
                    },
                )
                data = response.json()
                comments = data.get("response", {}).get("items", [])

                # Ищем, есть ли в массиве комментариев автор с нашим vk_id
                user_commented = any(
                    str(comment.get("from_id")) == str(vk_id) for comment in comments
                )

                if user_commented:
                    total_score += 3.0  # 3 балла за комментарий

    return total_score
