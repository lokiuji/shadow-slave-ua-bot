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
        
        # Шукаємо головний контейнер
        content_div = soup.find('div', class_='txt') or soup.find('div', id='article') or soup.find('div', id='chr-content')
            
        if not content_div:
            print("❌ Текст не знайдено на сторінці (можливо, невірна адреса).")
            return None, None

        # Очищаємо дуже обережно (не чіпаємо div та a)
        for tag in content_div(["script", "style", "button", "iframe", "ins", "form"]):
            tag.decompose()
            
        # Спочатку пробуємо зібрати всі абзаци <p> (це найчистіший спосіб)
        paragraphs = content_div.find_all('p')
        if paragraphs:
            text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        else:
            # Якщо <p> немає, беремо просто текст з блоку
            text = content_div.get_text(separator='\n\n', strip=True)
            
        if not text:
             print("❌ Блок знайдено, але текст пустий.")
             return None, None
        
        title = "Shadow Slave Chapter"
        title_tag = soup.find('h1', class_='tit') or soup.find('h1')
        if title_tag:
            title = title_tag.text.strip()
            
        print(f"✅ Успіх! Скачано символів: {len(text)}")
        return title, text

    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None, None

def get_novelbin_chapter(chapter_number):
    url = f"https://freewebnovel.com/shadow-slave/chapter-{chapter_number}.html"
    return get_text_from_url(url)