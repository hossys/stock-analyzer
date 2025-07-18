import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)
CHARTS_DIR = "charts"

STOCK_SYMBOLS = ["AAPL", "GOOGL", "MSFT", "NVDA", "AMZN", "TSLA", "AMD", "COIN", "LCID"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /plot to choose a stock chart.")

async def plot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for i in range(0, len(STOCK_SYMBOLS), 2):
        row = []
        for symbol in STOCK_SYMBOLS[i:i+2]:
            row.append(InlineKeyboardButton(text=symbol, callback_data=symbol))
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📊 Choose a stock to view its chart:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data
    image_path = os.path.join(CHARTS_DIR, f"{symbol}.png")

    if os.path.exists(image_path):
        await query.message.reply_photo(photo=open(image_path, "rb"))
    else:
        await query.message.reply_text(f"❌ Chart for {symbol} not found.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plot", plot))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("✅ Bot is running. Use /plot to get charts.")
    app.run_polling()

if __name__ == "__main__":
    main()