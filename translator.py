import os
import time
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv

# Завантажуємо ключі з .env
load_dotenv()

# Налаштування
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """
Ти професійний перекладач ранобе. Твоя задача — перекласти текст українською мовою.
ГЛОСАРІЙ ТА ПРАВИЛА ДЛЯ "SHADOW SLAVE":
1. Sunny -> Санні (чоловічий рід).
2. Nephis -> Нефіс (жіночий рід).
3. Cassie -> Кессі.
4. Nightmare Spell -> Кошмарне Закляття.
5. Awakened -> Пробуджений.
6. Legacy -> Спадок.
7. Aspect -> Аспект.
8. Flaw -> Вада.
9. Weaver -> Ткач.
10. Soul Sea -> Море Душі.
Стиль: художній, похмурий, зберігай атмосферу. Не роби дослівний переклад ідіом.
"""

def split_text(text, max_chunk_size=3000):
    """Розбиває текст на шматки, щоб не перевантажити запит."""
    chunks = []
    current_chunk = ""
    for paragraph in text.split('\n'):
        if len(current_chunk) + len(paragraph) < max_chunk_size:
            current_chunk += paragraph + "\n"
        else:
            chunks.append(current_chunk)
            current_chunk = paragraph + "\n"
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def translate_chunk(text_chunk, retries=5):
    """Перекладає шматок з повторними спробами при помилці 429."""
    attempt = 0
    while attempt < retries:
        try:
            full_prompt = f"{SYSTEM_PROMPT}\n\nТекст:\n{text_chunk}"
            response = model.generate_content(full_prompt)
            if response.text:
                return response.text
        except exceptions.ResourceExhausted:
            wait_time = (2 ** attempt) * 5
            print(f"⚠️ Ліміт Gemini. Чекаємо {wait_time} сек...")
            time.sleep(wait_time)
            attempt += 1
        except Exception as e:
            print(f"❌ Помилка: {e}")
            time.sleep(5)
            attempt += 1
    return "[ПОМИЛКА ПЕРЕКЛАДУ]"

def translate_full_chapter(full_text):
    chunks = split_text(full_text)
    translated_text = ""
    
    print(f"Розпочато переклад. Шматків: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        translated_part = translate_chunk(chunk)
        translated_text += translated_part + "\n\n"
        # Пауза між шматками, щоб не дратувати API
        time.sleep(2)
        
    return translated_text