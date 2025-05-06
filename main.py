import os
import json
import asyncio
import logging
import snscrape.modules.twitter as sntwitter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer

ACCOUNTS_FILE = 'accounts.json'
SENT_FILE = 'sent.json'
CHECK_INTERVAL = 30

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Завантаження акаунтів
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    with open(ACCOUNTS_FILE, 'r') as f:
        return json.load(f)

# Збереження акаунтів
def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f)

# Завантаження вже надісланих твітів
def load_sent():
    if not os.path.exists(SENT_FILE):
        return []
    with open(SENT_FILE, 'r') as f:
        return json.load(f)

# Збереження вже надісланих твітів
def save_sent(sent_ids):
    with open(SENT_FILE, 'w') as f:
        json.dump(sent_ids, f)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я відстежую акаунти Twitter. Використовуй /add, /remove, /list.")

# Команда /add
async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Вкажи акаунт, наприклад /add elonmusk")
    username = context.args[0].lstrip('@')
    accounts = load_accounts()
    if username not in accounts:
        accounts.append(username)
        save_accounts(accounts)
        await update.message.reply_text(f"Акаунт @{username} додано!")
    else:
        await update.message.reply_text("Цей акаунт вже є в списку.")

# Команда /remove
async def remove_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Вкажи акаунт, наприклад /remove elonmusk")
    username = context.args[0].lstrip('@')
    accounts = load_accounts()
    if username in accounts:
        accounts.remove(username)
        save_accounts(accounts)
        await update.message.reply_text(f"Акаунт @{username} видалено.")
    else:
        await update.message.reply_text("Цього акаунта немає в списку.")

# Команда /list
async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = load_accounts()
    if accounts:
        msg = "🔎 Відстежувані акаунти:\n" + "\\n".join(f"@{a}" for a in accounts)
    else:
        msg = "Список акаунтів порожній."
    await update.message.reply_text(msg)

# Перевірка нових твітів
async def check_tweets(app):
    sent = load_sent()
    while True:
        accounts = load_accounts()
        for username in accounts:
            try:
                for i, tweet in enumerate(sntwitter.TwitterUserScraper(username).get_items()):
                    if i > 2: break  # тільки останні 3 твіти
                    if str(tweet.id) not in sent:
                        url = f"https://twitter.com/{username}/status/{tweet.id}"
                        text = f"🧵 @{username} написав:\n\n{tweet.content}"
                        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Перейти в Twitter", url=url)]])
                        for chat_id in app.chat_ids:
                            await app.bot.send_message(chat_id=chat_id, text=text, reply_markup=btn)
                        sent.append(str(tweet.id))
            except Exception as e:
                logger.error(f"Помилка при перевірці @{username}: {e}")
        save_sent(sent)
        await asyncio.sleep(CHECK_INTERVAL)

# Імітація HTTP-сервера
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK")

async def start_http_server():
    httpd = HTTPServer(('0.0.0.0', 80), SimpleHTTPRequestHandler)
    httpd.serve_forever()

# Головна функція
async def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.chat_ids = set()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_account))
    app.add_handler(CommandHandler("remove", remove_account))
    app.add_handler(CommandHandler("list", list_accounts))

    async def register_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
        app.chat_ids.add(update.effective_chat.id)
    app.add_handler(CommandHandler("start", register_chat))

    asyncio.create_task(check_tweets(app))
    asyncio.create_task(start_http_server())  # Запускаємо HTTP-сервер

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
