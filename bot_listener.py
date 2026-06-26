"""
Background listener for the Telegram bot.
Waits for the /run command and executes the screener directly.
"""

import os
import logging
import time
import telebot
from dotenv import load_dotenv

# Import the actual screener functions directly
from stock_screener.utils.symbols import load_symbols
from stock_screener.data.pipeline import fetch_historical_data
from stock_screener.engine.screener import BreakoutScreener
from stock_screener.alerts.telegram import send_breakout_alert

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load the token from your existing .env file
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing in .env")

# Initialize the listener
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🤖 EOD Screener Bot is online.\nSend /run to trigger a fresh scan.")


@bot.message_handler(commands=['run'])
def handle_run_command(message):
    bot.reply_to(message, "⚙️ Screener starting! Fetching EOD data for 400+ stocks... This might take a minute.")
    
    try:
        # 1. Load symbols
        symbols = load_symbols()
        if not symbols:
            bot.reply_to(message, "❌ No symbols found. Check your symbols file.")
            return

        # 2. Fetch data (direct call, no subprocess)
        stock_data, benchmark_data = fetch_historical_data(symbols)
        
        if not stock_data:
            bot.reply_to(message, "❌ No stock data retrieved. Check your data pipeline.")
            return
        if benchmark_data.empty:
            bot.reply_to(message, "❌ Benchmark data (^NSEI) unavailable.")
            return

        # 3. Run the screener
        screener = BreakoutScreener(stock_data, benchmark_data)
        breakouts = screener.screen()

        # 4. Send the alert (this function already formats and pushes the Markdown report)
        # No need to reply here because send_breakout_alert already sends the report to the chat.
        if breakouts.empty:
            bot.reply_to(message, "📭 No breakouts today. All gates passed by zero stocks.")
        else:
            # The send_breakout_alert function should already handle pushing the results.
            # If it returns False, we catch it.
            sent = send_breakout_alert(breakouts)
            if not sent:
                bot.reply_to(message, "⚠️ Breakouts found, but Telegram alert failed to send. Check your .env credentials.")

    except Exception as e:
        logger.exception("Screener crashed during /run command.")
        bot.reply_to(message, f"❌ Screener crashed: {str(e)}")


if __name__ == "__main__":
    print("Bot is listening in the background... Send /run in Telegram.")
    
    # --- Fault-tolerant polling (prevents crash on Telegram API hiccups) ---
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Bot polling crashed: {e}. Restarting in 10 seconds...")
            time.sleep(10)