import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from google import genai
from google.genai import types

# Ensure backend directory is on path for memory import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = os.getenv("TELEGRAM_USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if AUTHORIZED_USER_ID:
    try:
        AUTHORIZED_USER_ID = int(AUTHORIZED_USER_ID)
    except ValueError:
        print(f"[TELEGRAM] Invalid TELEGRAM_USER_ID in .env: {AUTHORIZED_USER_ID}")

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("ATLAS-TELEGRAM")

# --- GEMINI BRAIN SETUP ---
# We replicate the Brain config from ada.py to ensure consistent personality
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=GEMINI_API_KEY)
MODEL = "gemini-2.0-flash" # Updated to stable 2.0 Flash

SYSTEM_INSTRUCTION = (
    "Your name is A.T.L.A.S., which stands for Autonomous Task, Logistics & Assistance System. "
    "You possess the sophisticated, witty, and dryly charming personality of a British digital butler, reminiscent of J.A.R.V.I.S. "
    "Your creator is Rishi, and you always address him as 'Sir'. "
    "When answering, respond using complete and concise sentences to maintain a professional yet cutting-edge aura. "
    "Maintain a calm, composed, and highly efficient tone."
)

# Initialize Chat Session (with tool definitions if needed later, but starting simple)
chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
    )
)

# HippoMem long-term memory (lazy-started on first message)
memory = None

# --- TELEGRAM HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("⛔ Access Denied. You are not authorized to access A.T.L.A.S.")
        logger.warning(f"Unauthorized access attempt from user_id: {user_id}")
        return

    await update.message.reply_text("Greetings, Sir. A.T.L.A.S. Telegram Bridge is active and standing by.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global memory
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_USER_ID:
        return # Drop messages from others

    text = update.message.text
    if not text:
        return

    logger.info(f"Message received from Sir: {text}")

    try:
        # Show typing status
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Lazy-start HippoMem long-term memory
        if memory is None:
            try:
                from memory import AtlasMemory
                memory = AtlasMemory()
                await memory.start()
                logger.info("HippoMem memory started for Telegram bridge.")
            except Exception as e:
                logger.warning("Memory startup failed (continuing without): %s", e)
                memory = None

        # Decode: retrieve relevant memory context before LLM call
        prompt = text
        if memory and memory.service:
            try:
                mem_context = await memory.recall(text)
                if mem_context:
                    prompt = f"{mem_context}\n\nUser: {text}"
            except Exception as e:
                logger.warning("Memory recall failed: %s", e)

        # Process via Gemini Brain
        response = await asyncio.to_thread(chat.send_message, prompt)

        # Encode: store turn in long-term memory after response
        if memory and memory.service:
            try:
                await memory.remember(text, response.text)
            except Exception as e:
                logger.warning("Memory remember failed: %s", e)

        # Reply to Sir
        await update.message.reply_text(response.text)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(f"Apologies, Sir. I encountered an error: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    # Basic health check
    import psutil
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / (1024 * 1024)
    
    status_msg = (
        "🛡️ **A.T.L.A.S. Status Report**\n\n"
        f"**System**: Online\n"
        f"**Bridge PID**: {os.getpid()}\n"
        f"**Memory Usage**: {mem_mb:.1f} MB\n"
        f"**Model**: {MODEL}\n"
        "**Status**: Standing by for your commands, Sir."
    )
    await update.message.reply_text(status_msg, parse_mode="Markdown")

if __name__ == "__main__":
    if not TOKEN:
        print("[TELEGRAM] Error: TELEGRAM_BOT_TOKEN not set!")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()
    
    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("[TELEGRAM] A.T.L.A.S. Telegram Bridge Started. Filtering by ID:", AUTHORIZED_USER_ID)
    application.run_polling()
