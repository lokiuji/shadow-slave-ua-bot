import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from telegraph import Telegraph

from translator import translate_full_chapter
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
        "Привіт! Надішли мені номер глави або пряме посилання на NovelBin."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    
    if ADMIN_ID and str(update.message.from_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⛔ Доступ заборонено.")
        return

    user_input = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ Обробляю запит...")

    try:
        eng_title, eng_text = "", ""

        if user_input.isdigit():
            await status_msg.edit_text(f"🔎 Шукаю главу {user_input} на NovelBin...")
            eng_title, eng_text = get_novelbin_chapter(user_input)
        elif user_input.startswith("http"):
            await status_msg.edit_text(f"🔗 Завантажую за посиланням...")
            eng_title, eng_text = get_text_from_url(user_input)
        else:
            await status_msg.edit_text("🔢 Надішли номер глави (цифрами) або пряме посилання.")
            return

        if not eng_text:
            await status_msg.edit_text("❌ Не вдалося завантажити текст. Перевір Cookies у .env!")
            return

        await status_msg.edit_text(f"📖 {eng_title}\n✨ Перекладаю...")
        ukr_text = translate_full_chapter(eng_text)
        
        if "[ПОМИЛКА ПЕРЕКЛАДУ]" in ukr_text:
             await status_msg.edit_text("❌ Помилка Gemini API.")
             return

        await status_msg.edit_text("📝 Формую Telegraph...")
        
        html_content = ukr_text.replace('\n', '<br>')
        
        response = telegraph.create_page(
            title=f"Shadow Slave - {eng_title}",
            html_content=html_content,
            author_name='Shadow Slave UKR'
        )
        
        telegraph_url = response['url']
        post_text = f"🌑 **Shadow Slave - {eng_title}**\n\nЧитати переклад:\n👉 {telegraph_url}"
        
        if CHANNEL_ID:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=post_text, parse_mode='Markdown')
            await status_msg.edit_text(f"✅ Готово і відправлено в канал!\n{telegraph_url}")
        else:
            await status_msg.edit_text(f"✅ Готово!\n{telegraph_url}")
        
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