"""
Production entrypoint: Runs the Telegram bot listener + a scheduled daily screener.
"""
import os
import logging
import time
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Import your existing modules
from stock_screener.utils.symbols import load_symbols
from stock_screener.data.pipeline import fetch_historical_data
from stock_screener.engine.screener import BreakoutScreener
from stock_screener.alerts.telegram import send_breakout_alert

# Try to import bot_listener
try:
    from bot_listener import bot
except ImportError:
    bot = None
    logging.warning("bot_listener not found. Telegram bot will not run.")

# Setup logging for production
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("screener.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_screener_job():
    """The function that runs automatically at market close."""
    logger.info("🕒 Scheduled screener job started.")
    try:
        symbols = load_symbols()
        if not symbols:
            logger.error("No symbols loaded.")
            return

        stock_data, benchmark_data = fetch_historical_data(symbols)
        if not stock_data or benchmark_data.empty:
            logger.error("Data fetch failed.")
            return

        screener = BreakoutScreener(stock_data, benchmark_data)
        breakouts = screener.screen()

        if breakouts.empty:
            logger.info("No breakouts found in scheduled run.")
        else:
            logger.info(f"Found {len(breakouts)} breakouts. Sending alert...")
            send_breakout_alert(breakouts)

    except Exception as e:
        logger.exception(f"Scheduled screener crashed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler = BackgroundScheduler()
    # Run at 4:00 PM IST (10:30 UTC) Monday to Friday
    scheduler.add_job(
        run_screener_job,
        trigger=CronTrigger(hour=10, minute=30, day_of_week='mon-fri', timezone='UTC')
    )
    scheduler.start()
    logger.info("📅 Scheduler started. Daily run set for 4:00 PM IST.")


def start_bot_listener():
    """Start the Telegram bot polling (runs forever)."""
    if bot is None:
        logger.warning("Bot not available. Skipping bot listener.")
        return

    logger.info("🤖 Telegram bot listener starting...")
    # This blocks forever. We'll run it in a separate thread.
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Bot polling crashed: {e}")


if __name__ == "__main__":
    logger.info("🚀 Production system booting up...")

    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    # Run the bot listener on the main thread (it blocks)
    # If bot is not available, just keep the scheduler running
    if bot:
        start_bot_listener()
    else:
        logger.info("Bot not available. Running scheduler only. Press Ctrl+C to stop.")
        # Keep the script alive
        while True:
            time.sleep(60)