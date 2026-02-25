import os
import time
from google import genai
from dotenv import load_dotenv
import itertools

load_dotenv()

key1 = os.getenv("GEMINI_API_KEY_1")
key2 = os.getenv("GEMINI_API_KEY_2")

clients = []
if key1: clients.append(genai.Client(api_key=key1))
if key2: clients.append(genai.Client(api_key=key2))

if not clients:
    print("❌ ПОМИЛКА: Не знайдено жодного GEMINI_API_KEY в .env")
    exit()

client_cycle = itertools.cycle(clients)

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

# НОВА ФУНКЦІЯ: Тільки для заголовків
def translate_title(title_text, retries=3):
    if not title_text or title_text.isdigit():
        return title_text

    attempt = 0
    while attempt < retries:
        try:
            # Промпт без згадки назви новели, щоб уникнути плутанини
            prompt = (
                "Ти — професійний перекладач літератури. Твоє завдання — перекласти назву розділу книги. "
                "Дотримуйся суворих правил:\n"
                "1. Видай ТІЛЬКИ переклад назви.\n"
                "2. Не додавай назву книги, серії чи авторів.\n"
                "3. Не використовуй лапки, крапки чи вступні фрази.\n\n"
                f"Текст для перекладу: {title_text}"
            )
            
            current_client = next(client_cycle)
            response = current_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            if response.text:
                result = response.text.strip().strip('"').strip("'").strip(".")
                
                # Жорстка фільтрація на випадок галюцинацій моделі
                forbidden_words = ["Тіньовий раб", "Shadow Slave", "Тіньовий Раб"]
                for word in forbidden_words:
                    result = result.replace(word, "")
                
                return result.strip("- ").strip()
        except Exception:
            time.sleep(2)
            attempt += 1
    return title_text

def translate_chunk(text_chunk, retries=5):
    attempt = 0
    while attempt < retries:
        try:
            full_prompt = f"{SYSTEM_PROMPT}\n\nТекст:\n{text_chunk}"
            current_client = next(client_cycle)
            response = current_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt
            )
            if response.text:
                return response.text
        except Exception as e:
            wait_time = (2 ** attempt) * 3
            print(f"⚠️ Помилка Gemini: {e}. Чекаємо {wait_time} сек...")
            time.sleep(wait_time)
            attempt += 1
    return "[ПОМИЛКА ПЕРЕКЛАДУ]"

def translate_full_chapter(full_text):
    chunks = split_text(full_text)
    translated_text = ""
    
    print(f"Розпочато переклад. Шматків: {len(chunks)}. Використовую {len(clients)} API ключ(ів).")
    
    for i, chunk in enumerate(chunks):
        translated_part = translate_chunk(chunk)
        translated_text += translated_part + "\n\n"
        time.sleep(1)
        
    return translated_text