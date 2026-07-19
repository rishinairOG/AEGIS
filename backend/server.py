import sys
import asyncio

# Fix for asyncio subprocess support on Windows
# MUST BE SET BEFORE OTHER IMPORTS
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import json
import signal
import asyncio
from datetime import datetime
from pathlib import Path

import socketio
import uvicorn
from fastapi import FastAPI

from logger import get_logger

logger = get_logger("server")



# Ensure we can import ada
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import atlas
from authenticator import FaceAuthenticator
from kasa_agent import KasaAgent
from memory import AtlasMemory

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
web_app = FastAPI()
app_socketio = socketio.ASGIApp(sio, web_app)

# --- SHUTDOWN HANDLER ---
def signal_handler(sig: int, frame) -> None:
    logger.info("Caught signal %s. Exiting gracefully...", sig)
    if app.audio_loop:
        try:
            app.audio_loop.stop()
        except Exception:
            pass
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

SETTINGS_FILE = "settings.json"


class AppServices:
    """Container for server-wide state; replaces module-level globals."""
    def __init__(self):
        self.settings = None
        self.kasa_agent = None
        self.authenticator = None
        self.memory = None
        self.audio_loop = None
        self.loop_task = None


app = AppServices()

DEFAULT_SETTINGS = {
    "face_auth_enabled": False, # Default OFF as requested
    "tool_permissions": {
        "generate_cad": True,
        "run_web_agent": True,
        "write_file": True,
        "read_directory": True,
        "read_file": True,
        "create_project": True,
        "switch_project": True,
        "list_projects": True
    },
    "printers": [], # List of {host, port, name, type}
    "kasa_devices": [], # List of {ip, alias, model}
    "camera_flipped": False, # Invert cursor horizontal direction
    "memory_enabled": True # HippoMem long-term memory
}

app.settings = DEFAULT_SETTINGS.copy()


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    if k == "tool_permissions" and isinstance(v, dict):
                        app.settings["tool_permissions"].update(v)
                    else:
                        app.settings[k] = v
            logger.info("Loaded settings: %s", list(app.settings.keys()))
        except Exception as e:
            logger.exception("Error loading settings")


def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(app.settings, f, indent=4)
        logger.info("Settings saved.")
    except Exception as e:
        logger.exception("Error saving settings")


# Load on startup
load_settings()
app.kasa_agent = KasaAgent(known_devices=app.settings.get("kasa_devices"))
# tool_permissions is now SETTINGS["tool_permissions"]

@web_app.on_event("startup")
async def startup_event():
    import sys
    logger.debug("Startup event triggered; Python %s", sys.version)
    try:
        loop = asyncio.get_running_loop()
        logger.debug("Running loop: %s", type(loop).__name__)
    except Exception as e:
        logger.debug("Loop check: %s", e)

    logger.info("Startup: Initializing Kasa Agent...")
    await app.kasa_agent.initialize()

    if app.settings.get("memory_enabled", True):
        try:
            app.memory = AtlasMemory()
            await app.memory.start()
            logger.info("HippoMem long-term memory started.")
        except Exception as e:
            logger.warning("Memory startup failed (continuing without): %s", e)
            app.memory = None

@web_app.get("/status")
async def status():
    return {"status": "running", "service": "A.T.L.A.S. Backend"}

@sio.event
async def connect(sid, environ):
    logger.info("Client connected: %s", sid)
    await sio.emit('status', {'msg': 'Connected to A.T.L.A.S. Backend'}, room=sid)

    async def on_auth_status(is_auth):
        logger.info("Auth status change: %s", is_auth)
        await sio.emit('auth_status', {'authenticated': is_auth})

    async def on_auth_frame(frame_b64):
        await sio.emit('auth_frame', {'image': frame_b64})

    if app.authenticator is None:
        app.authenticator = FaceAuthenticator(
            reference_image_path="reference.jpg",
            on_status_change=on_auth_status,
            on_frame=on_auth_frame
        )

    if app.authenticator.authenticated:
        await sio.emit('auth_status', {'authenticated': True})
    else:
        if app.settings.get("face_auth_enabled", False):
            await sio.emit('auth_status', {'authenticated': False})
            asyncio.create_task(app.authenticator.start_authentication_loop())
        else:
            logger.info("Face auth disabled; auto-authenticating.")
            await sio.emit('auth_status', {'authenticated': True})

@sio.event
async def disconnect(sid):
    logger.info("Client disconnected: %s", sid)

@sio.event
async def start_audio(sid, data=None):
    if app.settings.get("face_auth_enabled", False):
        if app.authenticator and not app.authenticator.authenticated:
            logger.warning("Blocked start_audio: not authenticated.")
            await sio.emit('error', {'msg': 'Authentication Required'})
            return

    logger.info("Starting Audio Loop...")
    device_index = None
    device_name = None
    if data:
        device_index = data.get('device_index')
        device_name = data.get('device_name')
    logger.info("Input device: name=%s index=%s", device_name, device_index)

    if app.audio_loop:
        if app.loop_task and (app.loop_task.done() or app.loop_task.cancelled()):
            logger.info("Audio loop task finished/cancelled; clearing and restarting.")
            app.audio_loop = None
            app.loop_task = None
        else:
            logger.info("Audio loop already running; re-connecting client.")
            await sio.emit('status', {'msg': 'A.T.L.A.S. Already Running'})
            return


    # Callback to send audio data to frontend
    def on_audio_data(data_bytes):
        # We need to schedule this on the event loop
        # This is high frequency, so we might want to downsample or batch if it's too much
        asyncio.create_task(sio.emit('audio_data', {'data': list(data_bytes)}))

    # Callback to send CAL data to frontend
    def on_cad_data(data):
        info = f"{len(data.get('vertices', []))} vertices" if 'vertices' in data else f"{len(data.get('data', ''))} bytes (STL)"
        logger.debug("Sending CAD data to frontend: %s", info)
        asyncio.create_task(sio.emit('cad_data', data))

    # Callback to send Browser data to frontend
    def on_web_data(data):
        logger.debug("Sending browser data to frontend: %d chars log", len(data.get('log', '')))
        asyncio.create_task(sio.emit('browser_frame', data))
        
    # Callback to send Transcription data to frontend
    def on_transcription(data):
        # data = {"sender": "User"|"ADA", "text": "..."}
        asyncio.create_task(sio.emit('transcription', data))

    # Callback to send Confirmation Request to frontend
    def on_tool_confirmation(data):
        # data = {"id": "uuid", "tool": "tool_name", "args": {...}}
        logger.info("Requesting confirmation for tool: %s", data.get('tool'))
        asyncio.create_task(sio.emit('tool_confirmation_request', data))

    # Callback to send CAD status to frontend
    def on_cad_status(status):
        # status can be: 
        # - a string like "generating" (from ada.py handle_cad_request)
        # - a dict with {status, attempt, max_attempts, error} (from CadAgent)
        if isinstance(status, dict):
            logger.debug("CAD status: %s (attempt %s/%s)", status.get('status'), status.get('attempt'), status.get('max_attempts'))
            asyncio.create_task(sio.emit('cad_status', status))
        else:
            # Legacy: simple string
            logger.debug("CAD status: %s", status)
            asyncio.create_task(sio.emit('cad_status', {'status': status}))

    # Callback to send CAD thoughts to frontend (streaming)
    def on_cad_thought(thought_text):
        asyncio.create_task(sio.emit('cad_thought', {'text': thought_text}))

    # Callback to send Project Update to frontend
    def on_project_update(project_name):
        logger.info("Project update: %s", project_name)
        asyncio.create_task(sio.emit('project_update', {'project': project_name}))

    # Callback to send Device Update to frontend
    def on_device_update(devices):
        # devices is a list of dicts
        logger.info("Kasa device update: %d devices", len(devices))
        asyncio.create_task(sio.emit('kasa_devices', devices))

    # Callback to send Error to frontend
    def on_error(msg):
        logger.warning("Sending error to frontend: %s", msg)
        asyncio.create_task(sio.emit('error', {'msg': msg}))

    try:
        logger.info("Initializing AudioLoop with device_index=%s", device_index)
        app.audio_loop = atlas.AudioLoop(
            video_mode="none",
            on_audio_data=on_audio_data,
            on_cad_data=on_cad_data,
            on_web_data=on_web_data,
            on_transcription=on_transcription,
            on_tool_confirmation=on_tool_confirmation,
            on_cad_status=on_cad_status,
            on_cad_thought=on_cad_thought,
            on_project_update=on_project_update,
            on_device_update=on_device_update,
            on_error=on_error,
            input_device_index=device_index,
            input_device_name=device_name,
            kasa_agent=app.kasa_agent,
            memory=app.memory
        )
        logger.info("AudioLoop initialized successfully.")
        app.audio_loop.update_permissions(app.settings["tool_permissions"])
        if data and data.get('muted', False):
            logger.info("Starting with audio paused")
            app.audio_loop.set_paused(True)
        logger.debug("Creating asyncio task for AudioLoop.run()")
        app.loop_task = asyncio.create_task(app.audio_loop.run())
        
        # Add a done callback to catch silent failures in the loop
        def handle_loop_exit(task):
            try:
                task.result()
            except asyncio.CancelledError:
                logger.info("Audio loop cancelled")
            except Exception as e:
                logger.exception("Audio loop crashed")
                # You could emit 'error' here if you have context
        
        app.loop_task.add_done_callback(handle_loop_exit)
        logger.info("A.T.L.A.S. started")
        await sio.emit('status', {'msg': 'A.T.L.A.S. Started'})
        saved_printers = app.settings.get("printers", [])
        if saved_printers and app.audio_loop.printer_agent:
            logger.info("Loading %d saved printers", len(saved_printers))
            for p in saved_printers:
                app.audio_loop.printer_agent.add_printer_manually(
                    name=p.get("name", p["host"]),
                    host=p["host"],
                    port=p.get("port", 80),
                    printer_type=p.get("type", "moonraker"),
                    camera_url=p.get("camera_url")
                )
        
        # Start Printer Monitor
        asyncio.create_task(monitor_printers_loop())
        
    except Exception as e:
        logger.exception("Critical error starting audio loop")
        await sio.emit('error', {'msg': f"Failed to start: {str(e)}"})
        app.audio_loop = None

async def monitor_printers_loop():
    """Background task to query printer status periodically."""
    logger.info("Starting printer monitor loop")
    while app.audio_loop and app.audio_loop.printer_agent:
        try:
            agent = app.audio_loop.printer_agent
            if not agent.printers:
                await asyncio.sleep(5)
                continue
                
            tasks = []
            for host, printer in agent.printers.items():
                if printer.printer_type.value != "unknown":
                    tasks.append(agent.get_print_status(host))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        pass # Ignore errors for now
                    elif res:
                        # res is PrintStatus object
                        await sio.emit('print_status_update', res.to_dict())
                        
        except asyncio.CancelledError:
            logger.info("Printer monitor cancelled")
            break
        except Exception as e:
            logger.warning("Monitor loop error: %s", e)
            
        await asyncio.sleep(2) # Update every 2 seconds for responsiveness

@sio.event
async def stop_audio(sid):
    if app.audio_loop:
        app.audio_loop.stop()
        logger.info("Stopping Audio Loop")
        app.audio_loop = None
        await sio.emit('status', {'msg': 'A.T.L.A.S. Stopped'})

@sio.event
async def pause_audio(sid):
    if app.audio_loop:
        app.audio_loop.set_paused(True)
        logger.info("Pausing audio")
        await sio.emit('status', {'msg': 'Audio Paused'})

@sio.event
async def resume_audio(sid):
    if app.audio_loop:
        app.audio_loop.set_paused(False)
        logger.info("Resuming audio")
        await sio.emit('status', {'msg': 'Audio Resumed'})

@sio.event
async def confirm_tool(sid, data):
    request_id = data.get('id')
    confirmed = data.get('confirmed', False)
    logger.debug("Confirm tool %s: %s", request_id, confirmed)
    if app.audio_loop:
        app.audio_loop.resolve_tool_confirmation(request_id, confirmed)
    else:
        logger.warning("Audio loop not active; cannot resolve confirmation.")

@sio.event
async def shutdown(sid, data=None):
    """Gracefully shutdown the server when the application closes."""
    logger.info("Shutdown signal received from frontend")
    if app.audio_loop:
        logger.info("Stopping Audio Loop...")
        app.audio_loop.stop()
        app.audio_loop = None
    if app.loop_task and not app.loop_task.done():
        logger.info("Cancelling loop task...")
        app.loop_task.cancel()
        app.loop_task = None
    if app.authenticator:
        logger.info("Stopping Authenticator...")
        app.authenticator.stop()
    logger.info("Graceful shutdown complete. Terminating process...")
    os._exit(0)

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    logger.debug("User input received: %s", text[:80] if text else "")
    if not app.audio_loop:
        logger.warning("Audio loop is None; cannot send text.")
        return
    if not app.audio_loop.session:
        logger.warning("Session is None; cannot send text.")
        return
    if text:
        logger.debug("Sending message to model")
        if app.audio_loop and app.audio_loop.project_manager:
            app.audio_loop.project_manager.log_chat("User", text)
        if app.audio_loop.memory and app.audio_loop.memory.service:
            try:
                context = await app.audio_loop.memory.recall(text)
                if context:
                    await app.audio_loop.session.send(
                        input=f"[Memory Context]: {context}",
                        end_of_turn=False,
                    )
            except Exception as e:
                logger.warning("Memory recall failed: %s", e)
        # INJECT VIDEO FRAME IF AVAILABLE (VAD-style logic for Text Input)
        if app.audio_loop and app.audio_loop._latest_image_payload:
            logger.debug("Piggybacking video frame with text input.")
            try:
                # Send frame first
                await app.audio_loop.session.send(input=app.audio_loop._latest_image_payload, end_of_turn=False)
            except Exception as e:
                logger.warning("Failed to send piggyback frame: %s", e)
                
        await app.audio_loop.session.send(input=text, end_of_turn=True)
        logger.debug("Message sent to model successfully.")

@sio.event
async def video_frame(sid, data):
    # data should contain 'image' which is binary (blob) or base64 encoded
    image_data = data.get('image')
    if image_data and app.audio_loop:
        asyncio.create_task(app.audio_loop.send_frame(image_data))

@sio.event
async def save_memory(sid, data):
    try:
        messages = data.get('messages', [])
        if not messages:
            logger.debug("No messages to save.")
            return

        # Ensure directory exists
        memory_dir = Path("long_term_memory")
        memory_dir.mkdir(exist_ok=True)

        # Generate filename
        # Use provided filename if available, else timestamp
        provided_name = data.get('filename')
        
        if provided_name:
            # Simple sanitization
            if not provided_name.endswith('.txt'):
                provided_name += '.txt'
            # Prevent directory traversal
            filename = memory_dir / Path(provided_name).name 
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = memory_dir / f"memory_{timestamp}.txt"

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in messages:
                sender = msg.get('sender', 'Unknown')
                text = msg.get('text', '')
                f.write(f"[{sender}]: {text}\n")
        logger.info("Conversation saved to %s", filename)
        await sio.emit('status', {'msg': 'Memory Saved Successfully'})

    except Exception as e:
        logger.exception("Error saving memory")
        await sio.emit('error', {'msg': f"Failed to save memory: {str(e)}"})

@sio.event
async def upload_memory(sid, data):
    logger.info("Received memory upload request")
    try:
        memory_text = data.get('memory', '')
        if not memory_text:
            logger.debug("No memory data provided.")
            return

        if not app.audio_loop:
            logger.warning("Audio loop is None; cannot load memory.")
            await sio.emit('error', {'msg': "System not ready (Audio Loop inactive)"})
            return
        if not app.audio_loop.session:
            logger.warning("Session is None; cannot load memory.")
            await sio.emit('error', {'msg': "System not ready (No active session)"})
            return
        logger.info("Sending memory context to model...")
        context_msg = f"System Notification: The user has uploaded a long-term memory file. Please load the following context into your understanding. The format is a text log of previous conversations:\n\n{memory_text}"
        await app.audio_loop.session.send(input=context_msg, end_of_turn=True)
        logger.info("Memory context sent successfully.")
        await sio.emit('status', {'msg': 'Memory Loaded into Context'})

    except Exception as e:
        logger.exception("Error uploading memory")
        await sio.emit('error', {'msg': f"Failed to upload memory: {str(e)}"})

@sio.event
async def discover_kasa(sid):
    logger.info("Received discover_kasa request")
    try:
        devices = await app.kasa_agent.discover_devices()
        await sio.emit('kasa_devices', devices)
        await sio.emit('status', {'msg': f"Found {len(devices)} Kasa devices"})
        
        # Save to settings
        # devices is a list of full device info dicts. minimizing for storage.
        saved_devices = []
        for d in devices:
            saved_devices.append({
                "ip": d["ip"],
                "alias": d["alias"],
                "model": d["model"]
            })
        
        # Merge with existing to preserve any manual overrides? 
        # For now, just overwrite with latest scan result + previously known if we want to be fancy,
        # but user asked for "Any new devices that are scanned are added there".
        # A simple full persistence of current state is safest.
        app.settings["kasa_devices"] = saved_devices
        save_settings()
        logger.info("Saved %d Kasa devices to settings", len(saved_devices))
        
    except Exception as e:
        logger.exception("Error discovering kasa")
        await sio.emit('error', {'msg': f"Kasa Discovery Failed: {str(e)}"})

@sio.event
async def iterate_cad(sid, data):
    # data: { prompt: "make it bigger" }
    prompt = data.get('prompt')
    logger.info("Received iterate_cad request: %s", (prompt or "")[:80])
    
    if not app.audio_loop or not app.audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        # Notify user work has started
        await sio.emit('status', {'msg': 'Iterating design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Call the agent with project path
        cad_output_dir = str(app.audio_loop.project_manager.get_current_project_path() / "cad")
        result = await app.audio_loop.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            logger.debug("Sending updated CAD data: %s", info)
            await sio.emit('cad_data', result)
            # Save to Project
            if 'file_path' in result:
                saved_path = app.audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    logger.info("Saved iterated CAD to %s", saved_path)

            await sio.emit('status', {'msg': 'Design updated'})
        else:
            await sio.emit('error', {'msg': 'Failed to update design'})
            
    except Exception as e:
        logger.exception("Error iterating CAD")
        await sio.emit('error', {'msg': f"Iteration Error: {str(e)}"})

@sio.event
async def generate_cad(sid, data):
    # data: { prompt: "make a cube" }
    prompt = data.get('prompt')
    logger.info("Received generate_cad request: %s", (prompt or "")[:80])
    
    if not app.audio_loop or not app.audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Generating new design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Use generate_prototype based on prompt with project path
        cad_output_dir = str(app.audio_loop.project_manager.get_current_project_path() / "cad")
        result = await app.audio_loop.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            logger.debug("Sending newly generated CAD data: %s", info)
            await sio.emit('cad_data', result)


            # Save to Project
            if 'file_path' in result:
                saved_path = app.audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    logger.info("Saved generated CAD to %s", saved_path)

            await sio.emit('status', {'msg': 'Design generated'})
        else:
            await sio.emit('error', {'msg': 'Failed to generate design'})
            
    except Exception as e:
        logger.exception("Error generating CAD")
        await sio.emit('error', {'msg': f"Generation Error: {str(e)}"})

@sio.event
async def prompt_web_agent(sid, data):
    # data: { prompt: "find xyz" }
    prompt = data.get('prompt')
    logger.info("Received web agent prompt: %s", (prompt or "")[:80])
    
    if not app.audio_loop or not app.audio_loop.web_agent:
        await sio.emit('error', {'msg': "Web Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Web Agent running...'})
        
        # We assume web_agent has a run method or similar.
        # This might block the loop if not strictly async or offloaded.
        # Ideally web_agent.run is async.
        # And it should emit 'browser_snap' and logs automatically via hooks if setup.
        
        # We might need to launch this as a task if it's long running?
        # asyncio.create_task(audio_loop.web_agent.run(prompt))
        # But we want to catch errors here.
        
        # Based on typical agent design, run() is the entry point.
        await app.audio_loop.web_agent.run(prompt)
        
        await sio.emit('status', {'msg': 'Web Agent finished'})
        
    except Exception as e:
        logger.exception("Error running Web Agent")
        await sio.emit('error', {'msg': f"Web Agent Error: {str(e)}"})

@sio.event
async def discover_printers(sid):
    logger.info("Received discover_printers request")
    
    if not app.audio_loop or not app.audio_loop.printer_agent:
        saved_printers = app.settings.get("printers", [])
        if saved_printers:
            # Convert saved printers to the expected format
            printer_list = []
            for p in saved_printers:
                printer_list.append({
                    "name": p.get("name", p["host"]),
                    "host": p["host"],
                    "port": p.get("port", 80),
                    "printer_type": p.get("type", "unknown"),
                    "camera_url": p.get("camera_url")
                })
            logger.info("Returning %d saved printers (audio_loop not ready)", len(printer_list))
            await sio.emit('printer_list', {'printers': printer_list, 'badge': False})
            return
        else:
            await sio.emit('printer_list', {'printers': [], 'badge': False})
            await sio.emit('status', {'msg': "Connect to A.T.L.A.S. to enable printer discovery"})
            return
        
    try:
        printers = await app.audio_loop.printer_agent.discover_printers()
        await sio.emit('printer_list', {'printers': printers, 'badge': True})
        await sio.emit('status', {'msg': f"Found {len(printers)} printers"})
    except Exception as e:
        logger.exception("Error discovering printers")
        await sio.emit('error', {'msg': f"Printer Discovery Failed: {str(e)}"})

@sio.event
async def add_printer(sid, data):
    # data: { host: "192.168.1.50", name: "My Printer", type: "moonraker" }
    raw_host = data.get('host')
    name = data.get('name') or raw_host
    ptype = data.get('type', "moonraker")
    
    # Parse port if present
    if ":" in raw_host:
        host, port_str = raw_host.split(":")
        port = int(port_str)
    else:
        host = raw_host
        port = 80
    
    logger.info("Received add_printer: %s:%s (%s)", host, port, ptype)
    
    if not app.audio_loop or not app.audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        # Add manually
        camera_url = data.get('camera_url')
        printer = app.audio_loop.printer_agent.add_printer_manually(name, host, port=port, printer_type=ptype, camera_url=camera_url)
        
        # Save to settings
        new_printer_config = {
            "name": name,
            "host": host,
            "port": port,
            "type": ptype,
            "camera_url": camera_url
        }
        
        # Check if already exists to avoid duplicates
        exists = False
        for p in app.settings.get("printers", []):
            if p["host"] == host and p["port"] == port:
                exists = True
                break
        
        if not exists:
            if "printers" not in app.settings:
                app.settings["printers"] = []
            app.settings["printers"].append(new_printer_config)
            save_settings()
            logger.info("Saved printer %s to settings", name)
        
        # Probe to confirm/correct type
        logger.info("Probing %s to confirm type", host)
        # Try port 7125 (Moonraker) and 4408 (Fluidd/K1) 
        ports_to_try = [80, 7125, 4408]
        
        actual_type = "unknown"
        for port in ports_to_try:
             found_type = await app.audio_loop.printer_agent._probe_printer_type(host, port)
             if found_type.value != "unknown":
                 actual_type = found_type
                 # Update port if different
                 if port != 80:
                     printer.port = port
                 break
        
        if actual_type != "unknown" and actual_type != printer.printer_type:
             printer.printer_type = actual_type
             logger.info("Corrected type to %s on port %s", actual_type.value, printer.port)
             
        # Refresh list for everyone
        printers = [p.to_dict() for p in app.audio_loop.printer_agent.printers.values()]
        await sio.emit('printer_list', {'printers': printers, 'badge': True})
        await sio.emit('status', {'msg': f"Added printer: {name}"})
        
    except Exception as e:
        logger.exception("Error adding printer")
        await sio.emit('error', {'msg': f"Failed to add printer: {str(e)}"})

@sio.event
async def print_stl(sid, data):
    logger.info("Received print_stl request: %s", list(data.keys()) if data else [])
    # data: { stl_path: "path/to.stl" | "current", printer: "name_or_ip", profile: "optional" }
    
    if not app.audio_loop or not app.audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        stl_path = data.get('stl_path', 'current')
        printer_name = data.get('printer')
        profile = data.get('profile')
        
        if not printer_name:
             await sio.emit('error', {'msg': "No printer specified"})
             return
             
        await sio.emit('status', {'msg': f"Preparing print for {printer_name}..."})
        
        # Get current project path for resolution
        current_project_path = None
        if app.audio_loop and app.audio_loop.project_manager:
            current_project_path = str(app.audio_loop.project_manager.get_current_project_path())
            logger.debug("Using project path: %s", current_project_path)

        # Resolve STL path before slicing so we can preview it
        resolved_stl = app.audio_loop.printer_agent._resolve_file_path(stl_path, current_project_path)
        
        if resolved_stl and os.path.exists(resolved_stl):
            # Open the STL in the CAD module for preview
            try:
                import base64
                with open(resolved_stl, 'rb') as f:
                    stl_data = f.read()
                stl_b64 = base64.b64encode(stl_data).decode('utf-8')
                stl_filename = os.path.basename(resolved_stl)
                
                logger.info("Opening STL in CAD module: %s", stl_filename)
                await sio.emit('cad_data', {
                    'format': 'stl',
                    'data': stl_b64,
                    'filename': stl_filename
                })
            except Exception as e:
                logger.warning("Could not preview STL: %s", e)
        
        # Progress Callback
        async def on_slicing_progress(percent, message):
            await sio.emit('slicing_progress', {
                'printer': printer_name,
                'percent': percent,
                'message': message
            })
            if percent < 100:
                 await sio.emit('status', {'msg': f"Slicing: {percent}%"})

        result = await app.audio_loop.printer_agent.print_stl(
            stl_path, 
            printer_name, 
            profile,
            progress_callback=on_slicing_progress,
            root_path=current_project_path
        )
        
        await sio.emit('print_result', result)
        await sio.emit('status', {'msg': f"Print Job: {result.get('status', 'unknown')}"})
        
    except Exception as e:
        logger.exception("Error printing STL")
        await sio.emit('error', {'msg': f"Print Failed: {str(e)}"})

@sio.event
async def get_slicer_profiles(sid):
    """Get available OrcaSlicer profiles for manual selection."""
    logger.info("Received get_slicer_profiles request")
    if not app.audio_loop or not app.audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
    
    try:
        profiles = app.audio_loop.printer_agent.get_available_profiles()
        await sio.emit('slicer_profiles', profiles)
    except Exception as e:
        logger.exception("Error getting slicer profiles")
        await sio.emit('error', {'msg': f"Failed to get profiles: {str(e)}"})

@sio.event
async def control_kasa(sid, data):
    # data: { ip, action: "on"|"off"|"brightness"|"color", value: ... }
    ip = data.get('ip')
    action = data.get('action')
    logger.info("Kasa control: %s -> %s", ip, action)
    
    try:
        success = False
        if action == "on":
            success = await app.kasa_agent.turn_on(ip)
        elif action == "off":
            success = await app.kasa_agent.turn_off(ip)
        elif action == "brightness":
            val = data.get('value')
            success = await app.kasa_agent.set_brightness(ip, val)
        elif action == "color":
            # value is {h, s, v} - convert to tuple for set_color
            h = data.get('value', {}).get('h', 0)
            s = data.get('value', {}).get('s', 100)
            v = data.get('value', {}).get('v', 100)
            success = await app.kasa_agent.set_color(ip, (h, s, v))
        
        if success:
            await sio.emit('kasa_update', {
                'ip': ip,
                'is_on': True if action == "on" else (False if action == "off" else None),
                'brightness': data.get('value') if action == "brightness" else None,
            })
 
        else:
             await sio.emit('error', {'msg': f"Failed to control device {ip}"})

    except Exception as e:
         logger.exception("Error controlling kasa")
         await sio.emit('error', {'msg': f"Kasa Control Error: {str(e)}"})

@sio.event
async def get_settings(sid):
    await sio.emit('settings', app.settings)

@sio.event
async def update_settings(sid, data):
    # Generic update
    logger.info("Updating settings: %s", list(data.keys()) if data else [])
    
    # Handle specific keys if needed
    if "tool_permissions" in data:
        app.settings["tool_permissions"].update(data["tool_permissions"])
        if app.audio_loop:
            app.audio_loop.update_permissions(app.settings["tool_permissions"])
            
    if "face_auth_enabled" in data:
        app.settings["face_auth_enabled"] = data["face_auth_enabled"]
        # If turned OFF, maybe emit auth status true?
        if not data["face_auth_enabled"]:
             await sio.emit('auth_status', {'authenticated': True})
             # Stop auth loop if running?
             if authenticator:
                 authenticator.stop() 

    if "camera_flipped" in data:
        app.settings["camera_flipped"] = data["camera_flipped"]
        logger.info("Camera flip set to: %s", data.get('camera_flipped'))

    save_settings()
    # Broadcast new full settings
    await sio.emit('settings', app.settings)


# Deprecated/Mapped for compatibility if frontend still uses specific events
@sio.event
async def get_tool_permissions(sid):
    await sio.emit('tool_permissions', app.settings["tool_permissions"])

@sio.event
async def update_tool_permissions(sid, data):
    logger.debug("Updating permissions (legacy): %s", data)
    app.settings["tool_permissions"].update(data)
    save_settings()
    
    if app.audio_loop:
        app.audio_loop.update_permissions(app.settings["tool_permissions"])
    await sio.emit('tool_permissions', app.settings["tool_permissions"])

if __name__ == "__main__":
    uvicorn.run(
        "server:app_socketio", 
        host="127.0.0.1", 
        port=8000, 
        reload=False, # Reload enabled causes spawn of worker which might miss the event loop policy patch
        loop="asyncio",
        reload_excludes=["temp_cad_gen.py", "output.stl", "*.stl"]
    )
