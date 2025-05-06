from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os

TOTAL_POINTS = 142000
TOTAL_OBOL = 40
RATE = TOTAL_OBOL / TOTAL_POINTS

def convert_points_to_obol(points):
    return round(points * RATE, 2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Надішли мені кількість балів, і я скажу, скільки це obol.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        points = float(update.message.text)
        obol = convert_points_to_obol(points)
        await update.message.reply_text(f"{points} балів = {obol} obol")
    except ValueError:
        await update.message.reply_text("Будь ласка, введи число.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
