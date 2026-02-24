from curl_cffi import requests
from bs4 import BeautifulSoup

def get_text_from_url(url):
    print(f"📡 curl_cffi: Завантажую {url}...")
    
    try:
        # Імітуємо Chrome, щоб не отримувати 403
        response = requests.get(
            url, 
            impersonate="chrome120", 
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ Помилка: Код {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Шукаємо текст (на Ranobes він зазвичай в div id="arrticle" або class="block_txt")
        content_div = soup.find('div', id='arrticle')
        if not content_div:
            content_div = soup.find('div', class_='block_txt')
            
        if not content_div:
            # Резервний пошук для інших сайтів (наприклад, freewebnovel)
            content_div = soup.find('div', class_='txt') or soup.find('div', id='chr-content')
            
        if not content_div:
            print("❌ Текст не знайдено на сторінці.")
            return None, None

        # Очищаємо від сміття
        for tag in content_div(["script", "style", "div", "a", "button", "iframe", "ins"]):
            tag.decompose()
            
        text = content_div.get_text(separator='\n\n').strip()
        
        # Назва глави
        title = "Shadow Slave Chapter"
        title_tag = soup.find('h1') or soup.find('span', class_='title')
        if title_tag:
            title = title_tag.text.strip()
            
        print(f"✅ Успіх! Скачано символів: {len(text)}")
        return title, text

    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None, None

def get_novelbin_chapter(chapter_number):
    # Змінюємо джерело за замовчуванням на Ranobes
    # Функцію залишаємо з тією ж назвою, щоб не зламати bot.py
    url = f"https://ranobes.top/chapters/shadow-slave/chapter-{chapter_number}/"
    return get_text_from_url(url)