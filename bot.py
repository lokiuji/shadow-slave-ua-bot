import os
import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from telegraph import Telegraph

from translator import translate_full_chapter, translate_title
from scraper import get_novelbin_chapter, get_text_from_url 

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

telegraph = Telegraph()
telegraph.create_account(short_name='ShadowSlaveBot')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Файл, де бот буде запам'ятовувати поточну главу (щоб не забути після перезапуску)
STATE_FILE = "current_chapter.txt"

def get_current_chapter():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return int(f.read().strip())
    except Exception as e:
        print(f"Помилка читання файлу стану: {e}")
    return 1 # Якщо файлу немає, починаємо з 1

def save_current_chapter(chapter_num):
    with open(STATE_FILE, "w") as f:
        f.write(str(chapter_num))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Надішли номер глави, посилання, або використай команди:\n"
        "▶️ /auto [номер] - Запустити спідран-переклад (1 глава кожні 5 сек)\n"
        "⏸ /stop - Зупинити авто-переклад"
    )

# --- АВТОМАТИЧНА ФУНКЦІЯ (ПЛАНУВАЛЬНИК) ---
async def auto_translate_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    chapter_num = get_current_chapter()
    
    await context.bot.send_message(chat_id=chat_id, text=f"🤖 Спідран-режим: Починаю главу {chapter_num}...")
    
    try:
        eng_title, eng_text = get_novelbin_chapter(str(chapter_num))
        
        if not eng_text:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Не вдалося знайти главу {chapter_num}. Можливо, це кінець? Зупиняю автопілот.")
            return

        # Парсинг заголовка
        match = re.search(r'(?:Chapter|Ch\.?)\s*(\d+)\s*[:\-]?\s*(.*)', eng_title, re.IGNORECASE)
        if match:
            c_num = match.group(1)
            chapter_name_eng = match.group(2).strip()
        else:
            c_num = str(chapter_num)
            chapter_name_eng = eng_title

        if chapter_name_eng:
            # Викликаємо нашу нову сувору функцію
            ukr_name = translate_title(chapter_name_eng)
            
            # Формуємо рядок самі: "Глава X - Назва"
            # Якщо переклад назви чомусь дублює номер, лишаємо тільки назву
            formatted_subtitle = f"Глава {chapter_num} - {ukr_name}"
        else:
            formatted_subtitle = f"Глава {chapter_num}"

        # Переклад
        ukr_text = translate_full_chapter(eng_text)
        
        if "[ПОМИЛКА ПЕРЕКЛАДУ]" in ukr_text:
             await context.bot.send_message(chat_id=chat_id, text=f"❌ Помилка API на главі {chapter_num}. Спробую ще раз через 30 сек.")
             context.job_queue.run_once(auto_translate_job, 30, chat_id=chat_id, name="auto_translation")
             return

        # Формування Telegraph
        html_content = (
            f"<h3>Тіньовий Раб (Shadow Slave)</h3>"
            f"<h4>{formatted_subtitle}</h4><hr><br>"
            + ukr_text.replace('\n\n', '<br><br>').replace('\n', ' ')
        )
        response = telegraph.create_page(
            title=f"Shadow Slave | {formatted_subtitle}",
            html_content=html_content,
            author_name='Shadow Slave UKR'
        )
        telegraph_url = response['url']
        
        # Відправка в канал
        post_text = f"Тіньовий Раб - Shadow Slave\n{formatted_subtitle}\n\n👉 {telegraph_url}"
        
        if CHANNEL_ID:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=post_text)
            # Додаємо повідомлення тобі, щоб ти бачив, що бот живий
            await context.bot.send_message(chat_id=chat_id, text=f"✅ Глава {chapter_num} успішно опублікована в канал!")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"✅ Глава {chapter_num} готова!\n\n{post_text}")
            
        # Зберігаємо прогрес (наступна глава)
        save_current_chapter(chapter_num + 1)
        
        # МАГІЯ СПІДРАНУ: Одразу запускаємо наступну главу через 5 секунд
        # ПЕРЕКОНАЙСЯ, ЩО ЦЕЙ РЯДОК Є І ВІН НА ОДНОМУ РІВНІ ВІДСТУПУ З save_current_chapter
        context.job_queue.run_once(auto_translate_job, 5, chat_id=chat_id, name="auto_translation")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Критична помилка авто-режиму: {str(e)}")
# --- КОМАНДИ ДЛЯ КЕРУВАННЯ ---
async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID): return
    
    # Якщо користувач передав номер глави (напр. /auto 150)
    if context.args and context.args[0].isdigit():
        save_current_chapter(int(context.args[0]))
    
    current = get_current_chapter()
    chat_id = update.effective_chat.id
    
    # Видаляємо старі завдання, якщо вони були
    current_jobs = context.job_queue.get_jobs_by_name("auto_translation")
    for job in current_jobs:
        job.schedule_removal()
        
    # Запускаємо першу главу прямо зараз (через 1 секунду)
    context.job_queue.run_once(auto_translate_job, 1, chat_id=chat_id, name="auto_translation")
    
    await update.message.reply_text(f"🚀 Режим кулемета увімкнено! Починаємо з глави {current}. Перерва між главами: 5 секунд.")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID): return
    
    current_jobs = context.job_queue.get_jobs_by_name("auto_translation")
    if not current_jobs:
        await update.message.reply_text("Автопілот і так вимкнений.")
        return
        
    for job in current_jobs:
        job.schedule_removal()
        
    await update.message.reply_text(f"⏸ Автопілот зупинено. Наступною буде глава {get_current_chapter()}.")

# --- РУЧНА ОБРОБКА ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID): return

    user_input = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ Обробляю запит (Ручний режим)...")

    try:
        eng_title, eng_text = "", ""

        if user_input.isdigit():
            await status_msg.edit_text(f"🔎 Шукаю главу {user_input}...")
            eng_title, eng_text = get_novelbin_chapter(user_input)
        elif user_input.startswith("http"):
            await status_msg.edit_text(f"🔗 Завантажую за посиланням...")
            eng_title, eng_text = get_text_from_url(user_input)
        else:
            await status_msg.edit_text("🔢 Надішли номер глави (цифрами) або пряме посилання.")
            return

        if not eng_text:
            await status_msg.edit_text("❌ Не вдалося завантажити текст.")
            return

        match = re.search(r'(?:Chapter|Ch\.?)\s*(\d+)\s*[:\-]?\s*(.*)', eng_title, re.IGNORECASE)
        if match:
            chapter_num = match.group(1)
            chapter_name_eng = match.group(2).strip()
        else:
            chapter_num = user_input if user_input.isdigit() else "?"
            chapter_name_eng = eng_title

        await status_msg.edit_text(f"📖 Знайдено: Глава {chapter_num}\n✨ Перекладаю назву та текст...")
        
        if chapter_name_eng:
            ukr_chapter_name = translate_chunk(chapter_name_eng).strip()
            ukr_chapter_name = ukr_chapter_name.replace("**", "").replace("*", "")
            formatted_subtitle = f"Глава {chapter_num} - {ukr_chapter_name}"
        else:
            formatted_subtitle = f"Глава {chapter_num}"

        ukr_text = translate_full_chapter(eng_text)
        if "[ПОМИЛКА ПЕРЕКЛАДУ]" in ukr_text:
             await status_msg.edit_text("❌ Помилка Gemini API.")
             return

        await status_msg.edit_text("📝 Формую Telegraph...")
        html_content = (
            f"<h2>Тіньовий Раб - Shadow Slave</h2>"
            f"<h3>{formatted_subtitle}</h3><hr><br>"
            + ukr_text.replace('\n', '<br>')
        )
        response = telegraph.create_page(
            title=f"Shadow Slave | {formatted_subtitle}",
            html_content=html_content,
            author_name='Shadow Slave UKR'
        )
        telegraph_url = response['url']
        post_text = f"Тіньовий Раб - Shadow Slave\n{formatted_subtitle}\n\n👉 {telegraph_url}"
        
        if CHANNEL_ID:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=post_text)
            await status_msg.edit_text(f"✅ Готово і відправлено в канал!\n{telegraph_url}")
        else:
            await status_msg.edit_text(f"✅ Готово!\n\n{post_text}")
        
    except Exception as e:
        error_text = f"❌ Критична помилка: {str(e)}"
        print(error_text)
        await status_msg.edit_text(error_text)

if __name__ == '__main__':
    if not TOKEN:
        print("Помилка: Немає токена в .env")
        exit()

    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('auto', cmd_auto))
    application.add_handler(CommandHandler('stop', cmd_stop))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🤖 Бот запущено! Чекаю на команди...")
    application.run_polling()