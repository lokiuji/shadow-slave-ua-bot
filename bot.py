import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from translator import translate_full_chapter

# Завантаження змінних
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Логування (щоб бачити помилки в консолі)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я бот-перекладач Shadow Slave.\n"
        "Просто надішли мені текст глави (англійською), і я перекладу її, дотримуючись глосарію."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    if len(user_text) < 50:
        await update.message.reply_text("Текст занадто короткий для перекладу.")
        return

    status_msg = await update.message.reply_text("⏳ Починаю переклад... Це може зайняти хвилину.")
    
    # Виконуємо переклад (це блокуюча операція, для великих ботів краще робити це в окремому потоці, але для пет-проєкту ок)
    try:
        translated_text = translate_full_chapter(user_text)
        
        # Телеграм має ліміт на довжину повідомлення (4096 символів).
        # Якщо переклад довгий, розбиваємо його.
        if len(translated_text) > 4000:
            for x in range(0, len(translated_text), 4000):
                await update.message.reply_text(translated_text[x:x+4000])
        else:
            await update.message.reply_text(translated_text)
            
        await status_msg.edit_text("✅ Переклад завершено!")
        
    except Exception as e:
        await status_msg.edit_text(f"Сталася помилка: {str(e)}")

if __name__ == '__main__':
    if not TOKEN:
        print("Помилка: Токен Telegram не знайдено в .env")
        exit()
        
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(msg_handler)
    
    print("Бот запущено...")
    application.run_polling()