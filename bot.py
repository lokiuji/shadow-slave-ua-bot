import os
import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from telegraph import Telegraph

# Зверни увагу: ми додали імпорт translate_chunk для перекладу заголовка
from translator import translate_full_chapter, translate_chunk
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Надішли мені номер глави або пряме посилання."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    
    # Перевірка на адміна
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⛔ Доступ заборонено.")
        return

    user_input = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ Обробляю запит...")

    try:
        eng_title, eng_text = "", ""

        # Вибір методу пошуку
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

        # --- РОЗУМНЕ ФОРМАТУВАННЯ ЗАГОЛОВКА ---
        # Шукаємо слово Chapter/Ch, беремо цифри, і все що після них - це назва
        match = re.search(r'(?:Chapter|Ch\.?)\s*(\d+)\s*[:\-]?\s*(.*)', eng_title, re.IGNORECASE)
        
        if match:
            chapter_num = match.group(1)
            chapter_name_eng = match.group(2).strip()
        else:
            chapter_num = user_input if user_input.isdigit() else "?"
            chapter_name_eng = eng_title

        await status_msg.edit_text(f"📖 Знайдено: Глава {chapter_num}\n✨ Перекладаю назву та текст...")
        
        # Перекладаємо назву глави (якщо вона є)
        if chapter_name_eng:
            ukr_chapter_name = translate_chunk(chapter_name_eng).strip()
            # Прибираємо зірочки, якщо ШІ вирішив зробити текст жирним
            ukr_chapter_name = ukr_chapter_name.replace("**", "").replace("*", "")
            formatted_subtitle = f"Глава {chapter_num} - {ukr_chapter_name}"
        else:
            formatted_subtitle = f"Глава {chapter_num}"

        # --- ПЕРЕКЛАД ТЕКСТУ ---
        ukr_text = translate_full_chapter(eng_text)
        
        if "[ПОМИЛКА ПЕРЕКЛАДУ]" in ukr_text:
             await status_msg.edit_text("❌ Помилка Gemini API.")
             return

        await status_msg.edit_text("📝 Формую Telegraph...")
        
        # --- ОФОРМЛЕННЯ TELEGRAPH ---
        # Додаємо форматований заголовок на самий початок тексту Telegraph
        html_content = (
            f"<h2>Тіньовий Раб - Shadow Slave</h2>"
            f"<h3>{formatted_subtitle}</h3><hr><br>"
            + ukr_text.replace('\n', '<br>')
        )
        
        response = telegraph.create_page(
            title=f"Shadow Slave | {formatted_subtitle}", # Заголовок вкладки в браузері
            html_content=html_content,
            author_name='Shadow Slave UKR'
        )
        
        telegraph_url = response['url']
        
        # --- ОФОРМЛЕННЯ POST-ПОВІДОМЛЕННЯ ---
        post_text = (
            f"Тіньовий Раб - Shadow Slave\n"
            f"{formatted_subtitle}\n\n"
            f"👉 {telegraph_url}"
        )
        
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
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🤖 Бот запущено! Чекаю на команди...")
    application.run_polling()