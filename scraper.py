from curl_cffi import requests
from bs4 import BeautifulSoup

def get_text_from_url(url):
    print(f"📡 curl_cffi (FreeWebNovel): Завантажую {url}...")
    
    try:
        response = requests.get(
            url, 
            impersonate="chrome120", 
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ Помилка: Код {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find('div', class_='txt') or soup.find('div', id='article') or soup.find('div', id='chr-content')
            
        if not content_div:
            print("❌ Текст не знайдено на сторінці (можливо, невірна адреса).")
            return None, None

        for tag in content_div(["script", "style", "button", "iframe", "ins", "form"]):
            tag.decompose()
            
        paragraphs = content_div.find_all('p')
        if paragraphs:
            text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        else:
            text = content_div.get_text(separator='\n\n', strip=True)
            
        if not text:
             print("❌ Блок знайдено, але текст пустий.")
             return None, None
        
        # --- ВИПРАВЛЕНО: ТОЧНИЙ ПОШУК НАЗВИ ---
        title = ""
        # Спочатку беремо тег <title> сторінки (Там завжди написано "Read Shadow Slave Chapter 1 Nightmare Begins...")
        if soup.title and soup.title.string:
            title = soup.title.string.split('-')[0].replace('Read', '').replace('online for free', '').strip()
        
        # Резервний варіант, якщо тегу немає
        if not title or "Chapter" not in title:
            title_tag = soup.find('span', class_='chapter') or soup.find('h3') or soup.find('h4') or soup.find('h1')
            title = title_tag.text.strip() if title_tag else "Shadow Slave Chapter"
            
        print(f"✅ Успіх! Скачано символів: {len(text)}. Знайдено заголовок: {title}")
        return title, text

    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None, None

def get_novelbin_chapter(chapter_number):
    url = f"https://freewebnovel.com/shadow-slave/chapter-{chapter_number}.html"
    return get_text_from_url(url)