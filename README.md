\# Shadow Slave Translator Bot



Telegram бот для автоматичного перекладу новели Shadow Slave з англійської на українську, використовуючи Google Gemini API.



\## Функціонал

\- Використовує Gemini 1.5 Flash.

\- Має вбудований глосарій (Sunny -> Санні, Nightmare Spell -> Кошмарне Закляття).

\- Обходить ліміти API (Rate Limits) через систему черг та повторних спроб.



\## Встановлення

1\. Клонуйте репозиторій.

2\. `pip install -r requirements.txt`

3\. Створіть `.env` файл з `TELEGRAM\_TOKEN` та `GEMINI\_API\_KEY`.

4\. `python bot.py`

