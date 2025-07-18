import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)

CHARTS_DIR = "charts"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /plot SYMBOL to get the latest chart. Example:\n/plot NVDA")

async def plot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Please provide a stock symbol. Example:\n/plot TSLA")
        return

    symbol = context.args[0].upper()
    image_path = os.path.join(CHARTS_DIR, f"{symbol}.png")

    if not os.path.exists(image_path):
        await update.message.reply_text(f"No saved chart found for {symbol}.")
        return

    await update.message.reply_photo(photo=open(image_path, "rb"))

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plot", plot))
    print("Bot is running. Use /plot SYMBOL to request charts.")
    app.run_polling()

if __name__ == "__main__":
    main()