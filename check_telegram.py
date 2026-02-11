import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def check_bot():
    if not TOKEN or TOKEN == "your_token_here":
        print("Error: TELEGRAM_BOT_TOKEN not found or not set in .env")
        return

    try:
        bot = Bot(token=TOKEN)
        bot_info = await bot.get_me()
        print(f"Success! Connected to Telegram bot: @{bot_info.username} ({bot_info.first_name})")
    except Exception as e:
        print(f"Failed to connect to Telegram: {e}")

if __name__ == "__main__":
    asyncio.run(check_bot())
