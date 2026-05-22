"""
Диагностика VK API — лайки и комментарии.
Использование:
    python test_vk.py <ссылка_на_пост> <ссылка_на_vk_профиль> [likes|comments]
По умолчанию проверяются лайки.
Пример:
    python test_vk.py https://vk.ru/wall-186962504_14556 https://vk.ru/tanyatv02 likes
    python test_vk.py https://vk.ru/wall-186962504_14556 https://vk.ru/tanyatv02 comments
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import httpx
import vk_service


async def test_likes(client, user_id, owner_id, item_id):
    numeric_user_id = int(user_id)
    print(f"Ищем ID {numeric_user_id} среди лайков поста...")

    offset = 0
    found = False
    total = None

    while True:
        resp = await client.get(
            "https://api.vk.com/method/likes.getList",
            params={
                "type": "post",
                "owner_id": owner_id,
                "item_id": item_id,
                "access_token": vk_service.VK_SERVICE_TOKEN,
                "v": vk_service.VK_API_VERSION,
                "count": 100,
                "offset": offset,
                "filter": "likes",
                "extended": 0,
            },
        )
        data = resp.json()

        if "error" in data:
            code = data["error"].get("error_code")
            msg = data["error"].get("error_msg")
            print(f"ОШИБКА VK API (code {code}): {msg}")
            return

        resp_data = data.get("response", {})
        if total is None:
            total = resp_data.get("count", 0)
            print(f"Всего лайков: {total}")

        items = resp_data.get("items", [])
        print(f"  Страница offset={offset}: получено {len(items)} ID")

        if numeric_user_id in items:
            found = True
            break

        offset += len(items)
        if not items or offset >= total or offset >= 1000:
            break

    print()
    if found:
        print(f"РЕЗУЛЬТАТ: лайк НАЙДЕН — задание было бы одобрено.")
    else:
        print(f"РЕЗУЛЬТАТ: лайк НЕ найден среди {min(total or 0, 1000)} проверенных.")
        print("Убедитесь, что пользователь действительно поставил лайк этому посту.")


async def test_comments(client, user_id, owner_id, item_id):
    user_id_str = str(user_id)
    print(f"Ищем комментарии от ID {user_id_str} под постом...")

    # Получаем общее количество комментариев
    count_resp = await client.get(
        "https://api.vk.com/method/wall.getComments",
        params={
            "owner_id": owner_id,
            "post_id": item_id,
            "access_token": vk_service.VK_SERVICE_TOKEN,
            "v": vk_service.VK_API_VERSION,
            "count": 1,
        },
    )
    count_data = count_resp.json()

    if "error" in count_data:
        code = count_data["error"].get("error_code")
        msg = count_data["error"].get("error_msg")
        print(f"ОШИБКА VK API (code {code}): {msg}")
        if code == 15:
            print("-> Комментарии закрыты или доступ ограничен.")
        return

    total = count_data.get("response", {}).get("count", 0)
    print(f"Всего комментариев: {total}")

    if total == 0:
        print("РЕЗУЛЬТАТ: комментариев нет — задание было бы отклонено.")
        return

    offset = 0
    found = False
    max_check = min(total, 500)

    while offset < max_check:
        resp = await client.get(
            "https://api.vk.com/method/wall.getComments",
            params={
                "owner_id": owner_id,
                "post_id": item_id,
                "access_token": vk_service.VK_SERVICE_TOKEN,
                "v": vk_service.VK_API_VERSION,
                "count": 100,
                "offset": offset,
                "need_likes": 0,
                "extended": 0,
            },
        )
        data = resp.json()

        if "error" in data:
            code = data["error"].get("error_code")
            msg = data["error"].get("error_msg")
            print(f"ОШИБКА VK API (code {code}): {msg}")
            return

        comments = data.get("response", {}).get("items", [])
        print(f"  Страница offset={offset}: получено {len(comments)} комментариев")

        for c in comments:
            from_id = str(c.get("from_id", "")).lstrip("-")
            if from_id == user_id_str:
                found = True
                print(f"  Найден комментарий: \"{c.get('text', '')[:80]}\"")
                break

        if found:
            break

        offset += len(comments)
        if not comments:
            break

    print()
    if found:
        print("РЕЗУЛЬТАТ: комментарий НАЙДЕН — задание было бы одобрено.")
    else:
        print(f"РЕЗУЛЬТАТ: комментарий НЕ найден среди {min(total, 500)} проверенных.")
        print("Убедитесь, что пользователь оставил комментарий под этим постом.")


async def main():
    if len(sys.argv) < 3:
        print("Использование: python test_vk.py <ссылка_на_пост> <ссылка_на_vk_профиль> [likes|comments]")
        sys.exit(1)

    post_url = sys.argv[1]
    vk_profile = sys.argv[2]
    check_type = sys.argv[3] if len(sys.argv) > 3 else "likes"

    print(f"Токен: {vk_service.VK_SERVICE_TOKEN[:10]}...")
    print(f"Пост: {post_url}")
    print(f"Профиль VK: {vk_profile}")
    print(f"Тип проверки: {check_type}")
    print()

    owner_id, item_id = vk_service.parse_vk_url(post_url)
    print(f"owner_id={owner_id}, item_id={item_id}")
    if not owner_id:
        print("ОШИБКА: не удалось распарсить ссылку на пост.")
        print("Ссылка должна содержать 'wall-XXXXXX_YYYYYYY'")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        user_id = await vk_service.extract_user_id(vk_profile, client)
        print(f"user_id (числовой) = {user_id}")
        if not user_id:
            print("ОШИБКА: не удалось определить числовой ID пользователя.")
            print("Проверьте формат ссылки VK в профиле участника.")
            return

        print()
        if check_type == "comments":
            await test_comments(client, user_id, owner_id, item_id)
        else:
            await test_likes(client, user_id, owner_id, item_id)


asyncio.run(main())
