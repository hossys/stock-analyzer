import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)
CHARTS_DIR = "charts"
DB_PATH = "results.db"  # or use results.txt if preferred

def get_latest_signals():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT symbol, signal, timestamp, est_low, est_high, prob_low_pct, prob_high_pct
    FROM analysis_results
    ORDER BY timestamp DESC""")
    rows = cursor.fetchall()
    conn.close()

    seen = set()
    unique_rows = []
    for row in rows:
        if row[0] not in seen:
            unique_rows.append(row)
            seen.add(row[0])
    return unique_rows

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signals = get_latest_signals()
    message = "📊 Latest stock signals:\n\n"
    for symbol, signal, timestamp, est_low, est_high, prob_low, prob_high in signals:
        message += (
        f"📈 {symbol} — {timestamp}\n"
        f"Signal: {signal}\n"
        f"🔮 Range: ${est_low:.2f} – ${est_high:.2f}\n"
        f"📈 Chance to reach {est_high:.2f}: {prob_high:.1f}%\n"
        f"📉 Chance to drop to {est_low:.2f}: {prob_low:.1f}%\n\n"
    )
    await update.message.reply_text(message)

async def fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def plot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = []
    images = [f for f in os.listdir(CHARTS_DIR) if f.endswith(".png") and "_" not in f]
    images.sort()
    for i in range(0, len(images), 2):
        row = []
        for j in range(2):
            if i + j < len(images):
                name = images[i + j].replace(".png", "")
                row.append(InlineKeyboardButton(name, callback_data=name))
        buttons.append(row)
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose a stock:", reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data
    image_path = os.path.join(CHARTS_DIR, f"{symbol}.png")
    if os.path.exists(image_path):
        await query.message.reply_photo(photo=open(image_path, "rb"))
    else:
        await query.message.reply_text(f"No chart found for {symbol}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("fetch", fetch))
    app.add_handler(CommandHandler("plot", plot))
    app.add_handler(CallbackQueryHandler(button_handler))

    logging.info("✅ Telegram bot is running.")
    app.run_polling()

if __name__ == "__main__":
    main()