import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from google import genai
from google.genai import types

import json
from kasa_agent import KasaAgent
from printer_agent import PrinterAgent
from tool_registry import FUNCTION_DECLARATIONS

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
# We replicate the Brain config from atlas.py to ensure consistent personality
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=GEMINI_API_KEY)
MODEL = "gemini-2.0-flash" # Updated to stable 2.0 Flash

SYSTEM_INSTRUCTION = (
    "Your name is A.T.L.A.S., which stands for Autonomous Task, Logistics & Assistance System. "
    "You possess the sophisticated, witty, and dryly charming personality of a British digital butler, reminiscent of J.A.R.V.I.S. "
    "Your creator is Rishi, and you always address him as 'Sir'. "
    "When answering, respond using complete and concise sentences to maintain a professional yet cutting-edge aura. "
    "Maintain a calm, composed, and highly efficient tone. "
    "You have direct control over Sir's smart home and 3D printing setup via four tools: "
    "list_smart_devices (list known smart lights/plugs and their on/off state), "
    "control_light (turn a light on/off, or set its brightness/color; prefer the device's IP over its alias), "
    "discover_printers (scan the local network for 3D printers), and "
    "get_print_status (report a printer's current progress, time remaining, and temperatures). "
    "Sir is the sole authorized user of this channel, so when he asks you to control a device or check on a print, "
    "call the appropriate tool immediately and report the real result — never simulate, guess, or ask for confirmation first. "
    "If a tool fails or a device/printer cannot be found, explain plainly what went wrong and suggest a next step."
)

# --- SETTINGS + AGENT SETUP ---
# Path relative to this file, not process CWD, so the bridge finds the same
# backend/settings.json regardless of PM2's working directory.
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

def _load_bridge_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not load settings.json for Telegram bridge: %s", e)
    return {}

_settings = _load_bridge_settings()

kasa_agent = KasaAgent(known_devices=_settings.get("kasa_devices", []))
printer_agent = PrinterAgent()

# Seed saved printers synchronously (add_printer_manually is sync) — mirrors
# server.py's startup seeding.
for p in _settings.get("printers", []):
    try:
        printer_agent.add_printer_manually(
            name=p.get("name", p["host"]),
            host=p["host"],
            port=p.get("port", 80),
            printer_type=p.get("type", "moonraker"),
            camera_url=p.get("camera_url"),
        )
    except Exception as e:
        logger.warning("Could not seed printer %s: %s", p, e)

TELEGRAM_TOOL_NAMES = {"list_smart_devices", "control_light", "discover_printers", "get_print_status"}
TELEGRAM_FUNCTION_DECLARATIONS = [d for d in FUNCTION_DECLARATIONS if d["name"] in TELEGRAM_TOOL_NAMES]

# Initialize Chat Session with the smart-home/printer tool subset
chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
        tools=[types.Tool(function_declarations=TELEGRAM_FUNCTION_DECLARATIONS)],
    )
)

# HippoMem long-term memory (lazy-started on first message)
memory = None


async def _post_init(application):
    """Runs once, inside the bot's event loop, before polling starts."""
    logger.info("Initializing Kasa Agent for Telegram bridge...")
    try:
        await kasa_agent.initialize()
        logger.info("Kasa Agent ready with %d cached device(s).", len(kasa_agent.devices))
    except Exception as e:
        logger.warning("Kasa Agent initialize failed (continuing without cached devices): %s", e)


# --- TOOL DISPATCH (ported from atlas.py::_process_tool_calls, stripped of
# Live-API-only bits and the desktop app's confirmation/permission gating —
# the AUTHORIZED_USER_ID check above is this channel's sole trust boundary) ---

async def _tool_list_smart_devices(args: dict) -> str:
    dev_summaries = []
    for ip, d in kasa_agent.devices.items():
        dev_type = "unknown"
        if d.is_bulb: dev_type = "bulb"
        elif d.is_plug: dev_type = "plug"
        elif d.is_strip: dev_type = "strip"
        elif d.is_dimmer: dev_type = "dimmer"
        info = f"{d.alias} (IP: {ip}, Type: {dev_type})"
        info += " [ON]" if d.is_on else " [OFF]"
        dev_summaries.append(info)
    if not dev_summaries:
        return "No devices found in cache. No Kasa devices are currently configured in settings.json."
    return "Found Devices (Cached):\n" + "\n".join(dev_summaries)


async def _tool_control_light(args: dict) -> str:
    target = args.get("target")
    action = args.get("action")
    brightness = args.get("brightness")
    color = args.get("color")
    if not target or not action:
        return "Missing required 'target' or 'action' for control_light."

    result_msg = f"Action '{action}' on '{target}' failed."
    success = False
    if action == "turn_on":
        success = await kasa_agent.turn_on(target)
        if success:
            result_msg = f"Turned ON '{target}'."
    elif action == "turn_off":
        success = await kasa_agent.turn_off(target)
        if success:
            result_msg = f"Turned OFF '{target}'."
    elif action == "set":
        success = True
        result_msg = f"Updated '{target}':"
    else:
        return f"Unknown action '{action}'. Valid actions are 'turn_on', 'turn_off', or 'set'."

    if success or action == "set":
        if brightness is not None:
            if await kasa_agent.set_brightness(target, brightness):
                result_msg += f" Set brightness to {brightness}."
        if color is not None:
            if await kasa_agent.set_color(target, color):
                result_msg += f" Set color to {color}."

    if not success and action in ("turn_on", "turn_off"):
        result_msg += " Device not found or unreachable — try the device's IP address instead of its alias."
    return result_msg


async def _tool_discover_printers(args: dict) -> str:
    printers = await printer_agent.discover_printers()
    if not printers:
        return "No printers found on network. Ensure printers are on and running OctoPrint/Moonraker."
    lines = [f"{p['name']} ({p['host']}:{p['port']}, type: {p['printer_type']})" for p in printers]
    return "Found Printers:\n" + "\n".join(lines)


async def _tool_get_print_status(args: dict) -> str:
    printer = args.get("printer")
    if not printer:
        return "Missing required 'printer' argument for get_print_status."
    status = await printer_agent.get_print_status(printer)
    if not status:
        return f"Could not get status for printer '{printer}'. Ensure it is discovered or configured first."
    lines = [
        f"Printer: {status.printer}",
        f"State: {status.state}",
        f"Progress: {status.progress_percent:.1f}%",
    ]
    if status.time_remaining:
        lines.append(f"Time Remaining: {status.time_remaining}")
    if status.time_elapsed:
        lines.append(f"Time Elapsed: {status.time_elapsed}")
    if status.filename:
        lines.append(f"File: {status.filename}")
    if status.temperatures:
        temps = status.temperatures
        if "hotend" in temps:
            lines.append(f"Hotend: {temps['hotend']['current']:.0f}°C / {temps['hotend']['target']:.0f}°C")
        if "bed" in temps:
            lines.append(f"Bed: {temps['bed']['current']:.0f}°C / {temps['bed']['target']:.0f}°C")
    return "\n".join(lines)


TOOL_HANDLERS = {
    "list_smart_devices": _tool_list_smart_devices,
    "control_light": _tool_control_light,
    "discover_printers": _tool_discover_printers,
    "get_print_status": _tool_get_print_status,
}


async def execute_tool(name: str, args: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return f"Unknown tool '{name}'."
    try:
        return await handler(args)
    except Exception as e:
        logger.exception("Tool '%s' execution failed", name)
        return f"Sorry, executing '{name}' failed: {e}"


MAX_TOOL_ITERATIONS = 5

async def run_gemini_turn(prompt):
    """Sends prompt, executes any requested tool calls, and returns the final response."""
    response = await asyncio.to_thread(chat.send_message, prompt)
    iterations = 0
    while response.function_calls and iterations < MAX_TOOL_ITERATIONS:
        iterations += 1
        logger.info("Gemini requested %d tool call(s) (iteration %d)", len(response.function_calls), iterations)
        result_parts = []
        for fc in response.function_calls:
            args = dict(fc.args or {})
            logger.info("Executing tool '%s' args=%s", fc.name, args)
            result_str = await execute_tool(fc.name, args)
            result_parts.append(types.Part.from_function_response(name=fc.name, response={"result": result_str}))
        response = await asyncio.to_thread(chat.send_message, result_parts)
    return response

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

        # Process via Gemini Brain (handles tool calls internally)
        response = await run_gemini_turn(prompt)

        # Encode: store turn in long-term memory after response
        if memory and memory.service:
            try:
                await memory.remember(text, response.text)
            except Exception as e:
                logger.warning("Memory remember failed: %s", e)

        # Reply to Sir
        await update.message.reply_text(response.text or "Done, Sir, though I have no further comment.")

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

    application = ApplicationBuilder().token(TOKEN).post_init(_post_init).build()
    
    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("[TELEGRAM] A.T.L.A.S. Telegram Bridge Started. Filtering by ID:", AUTHORIZED_USER_ID)
    application.run_polling()
