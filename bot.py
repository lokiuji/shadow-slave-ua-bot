import os
import time
from google import genai
from dotenv import load_dotenv

# Завантажуємо ключі з .env
load_dotenv()

# Налаштування нового клієнта
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
    """Перекладає шматок з повторними спробами при помилці."""
    attempt = 0
    while attempt < retries:
        try:
            full_prompt = f"{SYSTEM_PROMPT}\n\nТекст:\n{text_chunk}"
            # Використання нового формату генерації
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=full_prompt
            )
            if response.text:
                return response.text
        except Exception as e:
            wait_time = (2 ** attempt) * 5
            print(f"⚠️ Помилка Gemini: {e}. Чекаємо {wait_time} сек...")
            time.sleep(wait_time)
            attempt += 1
    return "[ПОМИЛКА ПЕРЕКЛАДУ]"

def translate_full_chapter(full_text):
    chunks = split_text(full_text)
    translated_text = ""
    
    print(f"Розпочато переклад. Шматків: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        translated_part = translate_chunk(chunk)
        translated_text += translated_part + "\n\n"
        time.sleep(2)
        
    return translated_text