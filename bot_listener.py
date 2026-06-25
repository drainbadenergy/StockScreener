"""
Background listener for the Telegram bot.
Waits for the /run command and executes the screener.
"""

import os
import subprocess
import telebot
from dotenv import load_dotenv

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
        # This triggers your existing script exactly as if you typed it in the terminal
        subprocess.run(["python", "run_screener.py"], check=True)
        # We don't need to send a success message here because run_screener.py 
        # already pushes the final formatted Markdown report directly to the chat!
        
    except subprocess.CalledProcessError as e:
        bot.reply_to(message, f"❌ Screener crashed while running. Error code: {e.returncode}")
    except Exception as e:
        bot.reply_to(message, f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Bot is listening in the background... Send /run in Telegram.")
    # infinity_polling keeps the script awake 24/7 waiting for your commands
    bot.infinity_polling()