import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Завантажуємо куки з .env
load_dotenv()

def get_text_from_url(url):
    print(f"📡 Requests (Cookie Mode): Стукаю на {url}...")

    # Беремо дані з .env
    cookie_str = os.getenv("NOVELBIN_COOKIE")
    user_agent = os.getenv("MY_USER_AGENT")

    if not cookie_str or not user_agent:
        print("❌ ПОМИЛКА: Не заповнені NOVELBIN_COOKIE або MY_USER_AGENT в .env файлі!")
        return None, None

    # Перетворюємо рядок куків у словник
    cookies = {}
    for item in cookie_str.split(';'):
        if '=' in item:
            name, value = item.strip().split('=', 1)
            cookies[name] = value

    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://novelbin.com/',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
    }

    try:
        # Робимо запит з твоїми куками (обходимо Cloudflare)
        response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        
        if response.status_code == 403:
            print("❌ Помилка 403. Куки прострочені або IP забанено.")
            print("💡 Порада: Онови NOVELBIN_COOKIE в .env зі свіжого браузера.")
            return None, None
            
        if response.status_code != 200:
            print(f"❌ Помилка: Код {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Шукаємо текст
        content_div = soup.find('div', id='chr-content')
        if not content_div:
            content_div = soup.find('div', id='chapter-content')
            
        if not content_div:
            print("❌ Текст не знайдено (можливо, куки не спрацювали або верстка змінилася).")
            return None, None

        # Очищаємо від сміття (реклама, приховані абзаци)
        for tag in content_div(["script", "style", "div", "a", "button", "iframe", "p.display-none"]):
            tag.decompose()
            
        text = content_div.get_text(separator='\n\n').strip()
        
        title = "Shadow Slave Chapter"
        title_tag = soup.find('span', class_='chr-text')
        if title_tag:
            title = title_tag.text.strip()
            
        print(f"✅ Успіх! Скачано символів: {len(text)}")
        return title, text

    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None, None

def get_novelbin_chapter(chapter_number):
    url = f"https://novelbin.com/b/shadow-slave/chapter-{chapter_number}"
    return get_text_from_url(url)