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
telegraph.create_account(short_name='Shadow Slave')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

STATE_FILE = "current_chapter.txt"

def get_current_chapter():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return int(f.read().strip())
    except Exception as e:
        print(f"Помилка читання файлу стану: {e}")
    return 1

def save_current_chapter(chapter_num):
    with open(STATE_FILE, "w") as f:
        f.write(str(chapter_num))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Надішли номер глави, посилання, або використай команди:\n"
        "▶️ /auto [номер] - Запустити авто-переклад\n"
        "⏸ /stop - Зупинити авто-переклад"
    )

async def auto_translate_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    chapter_num = get_current_chapter()
    
    await context.bot.send_message(chat_id=chat_id, text=f"🤖 Починаю главу {chapter_num}...")
    
    try:
        eng_title, eng_text = get_novelbin_chapter(str(chapter_num))
        
        if not eng_text:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Не вдалося знайти главу {chapter_num}.")
            return

        match = re.search(r'(?:Chapter|Ch\.?)\s*(\d+)\s*[:\-]?\s*(.*)', eng_title, re.IGNORECASE)
        if match:
            c_num = match.group(1)
            chapter_name_eng = match.group(2).strip()
        else:
            c_num = str(chapter_num)
            chapter_name_eng = eng_title.replace("Shadow Slave", "").strip(" -:")

        ukr_name = ""
        if chapter_name_eng:
            ukr_name = translate_title(chapter_name_eng)
        
        # ЯКЩО Є НАЗВА — СТАВИМО ДВОКРАПКУ, ЯКЩО НЕМА — ПРОСТО ГЛАВА
        if ukr_name:
            formatted_subtitle = f"Глава {c_num}: {ukr_name}"
        else:
            formatted_subtitle = f"Глава {c_num}"

        ukr_text = translate_full_chapter(eng_text)
        
        if "[ПОМИЛКА ПЕРЕКЛАДУ]" in ukr_text:
             await context.bot.send_message(chat_id=chat_id, text=f"❌ Помилка API. Спробую ще раз через 60 сек.")
             context.job_queue.run_once(auto_translate_job, 60, chat_id=chat_id, name="auto_translation")
             return

        # ІДЕАЛЬНЕ ОФОРМЛЕННЯ TELEGRAPH (БЕЗ ДУБЛІКАТІВ)
        paragraphs = [p.strip() for p in ukr_text.split('\n') if p.strip()]
        html_content = "".join([f"<p>{p}</p>" for p in paragraphs])
        
        response = telegraph.create_page(
            title=f"Тіньовий Раб | {formatted_subtitle}", # Telegraph сам зробить це головним заголовком
            html_content=html_content, # Тут тепер ТІЛЬКИ текст, без зайвих <h3>
            author_name='Shadow Slave UKR'
        )
        telegraph_url = response['url']
        
        post_text = f"📖 Тіньовий Раб\n🔖 {formatted_subtitle}\n\n👉 {telegraph_url}"
        
        if CHANNEL_ID:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=post_text)
            await context.bot.send_message(chat_id=chat_id, text=f"✅ Глава {chapter_num} успішно опублікована в канал!")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"✅ Глава {chapter_num} готова!\n\n{post_text}")
            
        save_current_chapter(chapter_num + 1)
        
        context.job_queue.run_once(auto_translate_job, 30, chat_id=chat_id, name="auto_translation")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Критична помилка авто-режиму: {str(e)}")

async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID): return
    
    if context.args and context.args[0].isdigit():
        save_current_chapter(int(context.args[0]))
    
    current = get_current_chapter()
    chat_id = update.effective_chat.id
    
    current_jobs = context.job_queue.get_jobs_by_name("auto_translation")
    for job in current_jobs:
        job.schedule_removal()
        
    context.job_queue.run_once(auto_translate_job, 1, chat_id=chat_id, name="auto_translation")
    
    await update.message.reply_text(f"🚀 Авто-режим увімкнено! Починаємо з глави {current}. Перерва між главами: 30 секунд.")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID): return
    
    current_jobs = context.job_queue.get_jobs_by_name("auto_translation")
    if not current_jobs:
        await update.message.reply_text("Автопілот і так вимкнений.")
        return
        
    for job in current_jobs:
        job.schedule_removal()
        
    await update.message.reply_text(f"⏸ Автопілот зупинено. Наступною буде глава {get_current_chapter()}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID): return

    user_input = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ Обробляю запит (Ручний режим)...")

    try:
        eng_title, eng_text = "", ""

        if user_input.isdigit():
            eng_title, eng_text = get_novelbin_chapter(user_input)
        elif user_input.startswith("http"):
            eng_title, eng_text = get_text_from_url(user_input)
        else:
            await status_msg.edit_text("🔢 Надішли номер глави (цифрами) або пряме посилання.")
            return

        if not eng_text:
            await status_msg.edit_text("❌ Не вдалося завантажити текст.")
            return

        match = re.search(r'(?:Chapter|Ch\.?)\s*(\d+)\s*[:\-]?\s*(.*)', eng_title, re.IGNORECASE)
        if match:
            c_num = match.group(1)
            chapter_name_eng = match.group(2).strip()
        else:
            c_num = user_input if user_input.isdigit() else "?"
            chapter_name_eng = eng_title.replace("Shadow Slave", "").strip(" -:")

        ukr_name = ""
        if chapter_name_eng:
            ukr_name = translate_title(chapter_name_eng)
        
        if ukr_name:
            formatted_subtitle = f"Глава {c_num}: {ukr_name}"
        else:
            formatted_subtitle = f"Глава {c_num}"

        ukr_text = translate_full_chapter(eng_text)
        if "[ПОМИЛКА ПЕРЕКЛАДУ]" in ukr_text:
             await status_msg.edit_text("❌ Помилка Gemini API.")
             return

        paragraphs = [p.strip() for p in ukr_text.split('\n') if p.strip()]
        html_content = "".join([f"<p>{p}</p>" for p in paragraphs])

        response = telegraph.create_page(
            title=f"Тіньовий Раб | {formatted_subtitle}",
            html_content=html_content,
            author_name='Shadow Slave UKR'
        )
        telegraph_url = response['url']
        post_text = f"📖 Тіньовий Раб\n🔖 {formatted_subtitle}\n\n👉 {telegraph_url}"
        
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