# A.T.L.A.S. — Codebase Context

> **A.T.L.A.S.** = **A**utonomous **T**ask, **L**ogistics & **A**ssistance **S**ystem
> Created by Rishi. Licensed MIT.

---

## Overview

A.T.L.A.S. is a multimodal AI desktop assistant built as an **Electron + React** frontend communicating with a **Python (FastAPI + Socket.IO)** backend. The AI backbone is **Google Gemini 2.5 Flash** with native real-time audio, vision, and tool-calling capabilities. The system integrates CAD generation, 3D printing, browser automation, smart home control, face authentication, and remote Telegram access.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18.2, Vite 5, Tailwind CSS 3.4, Three.js / R3F, Framer Motion, Lucide icons |
| **Desktop shell** | Electron 28 (frameless window, IPC for min/max/close) |
| **Backend** | Python 3.11, FastAPI, python-socketio (ASGI), uvicorn |
| **AI model** | Gemini 2.5 Flash (native audio via Live API), Gemini 3 Pro (CAD agent thinking), Gemini 2.5 Computer Use (web agent) |
| **CAD engine** | build123d (parametric Python CAD → STL export) |
| **Browser automation** | Playwright (headless Chromium) |
| **Smart home** | python-kasa (TP-Link Kasa devices) |
| **3D printing** | OrcaSlicer/PrusaSlicer CLI, Moonraker & OctoPrint REST APIs, mDNS discovery (zeroconf) |
| **Face auth** | MediaPipe Face Landmarker (cosine similarity on 468 landmarks) |
| **Hand gesture UI** | MediaPipe HandLandmarker (browser-side, GPU accelerated) |
| **Remote access** | python-telegram-bot |
| **Process manager** | PM2 via `ecosystem.config.js` |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Electron Shell  (electron/main.js)                  │
│  ┌────────────────────────────────────────────────┐  │
│  │  React Frontend  (src/)                        │  │
│  │  Socket.IO Client → localhost:8000             │  │
│  │  Components: Visualizer, Chat, CAD, Browser,   │  │
│  │  Kasa, Printer, Settings, Auth, Tools, etc.    │  │
│  │  MediaPipe HandLandmarker (gesture control)    │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────┬────────────────────────────────┘
                      │  Socket.IO (bidirectional)
┌─────────────────────▼────────────────────────────────┐
│  Python Backend  (backend/server.py)                  │
│  FastAPI + Socket.IO ASGI server on port 8000         │
│                                                       │
│  ┌─────────┐  ┌──────────┐  ┌──────────────┐        │
│  │ atlas.py│  │cad_agent │  │ web_agent.py │        │
│  │AudioLoop│  │  .py     │  │ (Playwright) │        │
│  │Gemini   │  │(build123d│  └──────────────┘        │
│  │Live API │  │ + Gemini)│                           │
│  └────┬────┘  └──────────┘  ┌──────────────┐        │
│       │                      │printer_agent │        │
│  ┌────┴────┐  ┌──────────┐  │  .py         │        │
│  │ tools.py│  │kasa_agent│  │(OrcaSlicer + │        │
│  │(tool    │  │  .py     │  │ Moonraker/   │        │
│  │ defs)   │  │(TP-Link) │  │ OctoPrint)   │        │
│  └─────────┘  └──────────┘  └──────────────┘        │
│                                                       │
│  ┌──────────────┐  ┌────────────────────┐            │
│  │authenticator │  │ project_manager.py │            │
│  │  .py         │  │ (file-based JSON   │            │
│  │(MediaPipe    │  │  project context)  │            │
│  │ Face Auth)   │  └────────────────────┘            │
│  └──────────────┘                                    │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Telegram Bridge  (backend/telegram_bridge.py)        │
│  Standalone daemon — Gemini 2.0 Flash chat session    │
│  Authorized by TELEGRAM_USER_ID                       │
└──────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
AEGIS/
├── backend/                    # Python backend (all agents + server)
│   ├── server.py               # FastAPI + Socket.IO ASGI server (AppServices container)
│   ├── atlas.py                # Core AudioLoop class — Gemini Live API session
│   ├── tool_registry.py        # Consolidated tool definitions + default permissions
│   ├── tools.py                # Re-exports from tool_registry (backward compat)
│   ├── logger.py               # Centralized backend logging
│   ├── memory.py               # HippoMem wrapper (AtlasMemory)
│   ├── cad_agent.py            # CAD generation via Gemini 3 Pro + build123d
│   ├── web_agent.py            # Browser automation via Gemini 2.5 Computer Use + Playwright
│   ├── kasa_agent.py           # TP-Link Kasa smart home control
│   ├── printer_agent.py        # 3D printer discovery, slicing, upload
│   ├── authenticator.py        # MediaPipe face authentication
│   ├── project_manager.py      # File-based project context management
│   ├── telegram_bridge.py      # Standalone Telegram bot bridge
│   ├── settings.json           # Runtime settings (persisted)
│   ├── verify_cad.py           # CAD installation verification utility
│   ├── verify_iteration_mock.py# Iteration mock test utility
│   ├── temp_cad_gen.py         # Temp CAD generation script
│   └── capture_face.py         # Face capture utility
│
├── src/                        # React frontend source
│   ├── App.jsx                 # Main application component (uses hooks)
│   ├── main.jsx                # React entry point (ErrorBoundary wrapper)
│   ├── index.css               # Global Tailwind + custom styles
│   ├── hooks/                  # React hooks (useSocket, useChat, useAuth, useCadState, etc.)
│   └── components/
│       ├── Visualizer.jsx      # 2D canvas fallback for central visualizer
│       ├── Visualizer3D.jsx    # R3F 3D audio-reactive sphere (primary)
│       ├── TopAudioBar.jsx     # Mic input waveform bar
│       ├── ChatModule.jsx      # Chat transcript + text input
│       ├── ToolsModule.jsx     # Bottom toolbar with action buttons
│       ├── DraggableWindow.jsx # Shared draggable overlay for CAD, Browser, etc.
│       ├── CadWindow.jsx       # 3D STL viewer (R3F) + iteration controls
│       ├── BrowserWindow.jsx   # Web agent screenshot viewer + prompt input
│       ├── KasaWindow.jsx      # Smart home device list + controls
│       ├── PrinterWindow.jsx   # 3D printer management + slicing controls
│       ├── SettingsWindow.jsx  # Device selection + settings modal
│       ├── ConfirmationPopup.jsx # Tool confirmation dialog
│       ├── ErrorBoundary.jsx   # React error boundary (fallback UI)
│       ├── AuthLock.jsx        # Face auth lock screen
│       └── MemoryPrompt.jsx    # (Deprecated) Memory save prompt
│
├── electron/
│   └── main.js                 # Electron main process — frameless window, IPC, backend health check
│
├── tests/                      # Pytest test suite
│   ├── conftest.py             # Shared fixtures (settings, temp dirs, sample STL)
│   ├── test_atlas_tools.py     # Tool definition tests
│   ├── test_web_agent.py       # Web agent tests
│   ├── test_kasa_agent.py      # Kasa agent tests
│   ├── test_cad_agent.py       # CAD agent tests
│   ├── test_printer_agent.py   # Printer agent tests
│   ├── test_authenticator.py   # Face auth tests
│   └── test_runner.py          # Test runner utility
│
├── projects/                   # User project data (auto-created, gitignored)
├── printer_profiles/           # 3D printer profile storage
├── public/                     # Static assets (hand_landmarker.task model)
├── dist/                       # Vite production build output
│
├── .env                        # API keys: GEMINI_API_KEY, FIRECRAWL_API_KEY, TELEGRAM_*
├── .env.example                # Template for .env
├── settings.json               # Persistent app settings (face auth, permissions, printers, kasa)
├── ecosystem.config.js         # PM2 process definitions (ATLAS-CORE + ATLAS-TELEGRAM)
├── package.json                # Node dependencies + scripts
├── requirements.txt            # Python dependencies
├── vite.config.js              # Vite config
├── tailwind.config.js          # Tailwind config
├── postcss.config.js           # PostCSS config
├── pytest.ini                  # Pytest configuration
└── README.md                   # Project documentation
```

---

## Key Modules Deep Dive

### `backend/atlas.py` — Core AI Engine

The heart of the system. Contains the `AudioLoop` class that:

- Establishes a persistent **Gemini Live API** session (WebSocket) using `google-genai` SDK v1beta
- Runs concurrent async tasks via `asyncio.TaskGroup`: audio capture (`listen_audio`), audio playback (`play_audio`), sending to Gemini (`send_realtime`), receiving from Gemini (`receive_audio`), and optionally camera/screen capture
- Implements **Voice Activity Detection (VAD)** — sends a camera frame to Gemini when speech starts (RMS threshold = 800)
- Handles **bi-directional transcription** — both user input and model output transcriptions are streamed to the frontend via Socket.IO, with delta calculation to handle Gemini's cumulative text behavior
- Manages **tool calling** — when Gemini invokes a function, the code dispatches to the appropriate agent and optionally requests user confirmation before execution
- Has an **auto-reconnect loop** with exponential backoff (1s → 10s cap), restoring recent chat history on reconnection
- Uses **Gemini's native audio mode** with 16kHz PCM input and 24kHz PCM output
- Model: `gemini-2.5-flash-native-audio-preview-12-2025`, voice: "Charon"
- System prompt: British J.A.R.V.I.S.-like butler personality, addresses user as "Sir"

### `backend/server.py` — WebSocket Gateway

- **FastAPI** app (`web_app`) wrapped in **python-socketio** ASGI app on port 8000; `app` is the `AppServices` container (no longer the FastAPI instance)
- Socket.IO events: `start_audio`, `stop_audio`, `pause_audio`, `resume_audio`, `user_input`, `video_frame`, `confirm_tool`, `shutdown`, `save_memory`, `upload_memory`, `discover_kasa`, `control_kasa`, `iterate_cad`, `generate_cad`, `prompt_web_agent`, `discover_printers`, `add_printer`, `print_stl`, `get_slicer_profiles`, `get_settings`, `update_settings`
- Manages global state: `AudioLoop` instance, `FaceAuthenticator`, `KasaAgent`, settings
- Loads/saves `settings.json` for persistence across restarts
- Background task: `monitor_printers_loop` polls printer status every 2 seconds

### `backend/cad_agent.py` — Parametric CAD Generation

- Uses **Gemini 3 Pro** with thinking enabled (`ThinkingConfig(include_thoughts=True)`) and streaming
- Prompts Gemini to write a `build123d` Python script, extracts the ```python code block, saves it as `current_design.py`
- Executes the script via `subprocess.run` using the current Python interpreter
- **Retry loop** (3 attempts): if script fails, sends the error back to Gemini for self-correction
- Supports both fresh generation (`generate_prototype`) and iterative modification (`iterate_prototype`) which reads the existing `current_design.py`
- Output: base64-encoded STL data sent to frontend for Three.js rendering
- Thoughts are streamed to the frontend in real-time via callbacks

### `backend/web_agent.py` — Browser Automation

- Uses **Gemini 2.5 Computer Use** model with Playwright headless Chromium
- Screen resolution: 1440×900, coordinates normalized to 0-1000 range
- Supports: navigation, clicking, typing, hovering, dragging, scrolling, keyboard combos
- Maximum 20 turns per task
- Screenshots sent as PNG to model and base64-encoded to frontend
- Safety decision auto-acknowledgement for model-requested confirmations

### `backend/printer_agent.py` — 3D Print Pipeline

- **Discovery**: mDNS via zeroconf (OctoPrint, Moonraker, Klipper, HTTP services)
- **Type probing**: hits `/printer/info` (Moonraker) and `/api/version` (OctoPrint) to identify unknown printers
- **Camera probing**: checks common MJPEG stream URLs
- **Slicing**: CLI invocation of OrcaSlicer or PrusaSlicer with auto-detected profiles
- **Profile matching**: score-based fuzzy matching of printer name to OrcaSlicer profile files (machine, process, filament)
- **Upload**: REST API upload to Moonraker (`/server/files/upload`) or OctoPrint (`/api/files/local`) with auto-start
- **Status monitoring**: polls Moonraker/OctoPrint for print progress, temperatures

### `backend/kasa_agent.py` — Smart Home Control

- Wraps `python-kasa` library for TP-Link Kasa devices (bulbs, plugs, strips, dimmers)
- Device resolution by IP address or alias (case-insensitive)
- Actions: turn on/off, set brightness (0-100), set color by name or HSV tuple
- Color name mapping: red, orange, yellow, green, cyan, blue, purple, pink, white, warm, cool, daylight
- Broadcast discovery with 5-second timeout, merges with cached devices

### `backend/authenticator.py` — Face Authentication

- Uses MediaPipe Face Landmarker (auto-downloads model on first run)
- Extracts 468 3D facial landmarks from reference image and live camera frames
- Comparison via **cosine similarity** with threshold 0.85 (1 - 0.15)
- Runs camera capture in a separate thread to avoid blocking async event loop
- Processes every other frame for performance
- Sends camera frames (base64 JPEG at 0.5x resolution) to frontend for display on lock screen

### `backend/project_manager.py` — Project Context

- File-based project management in `projects/` directory
- Each project has: `cad/` subfolder, `browser/` subfolder, `chat_history.jsonl` log
- Operations: create, switch, list projects; log chat entries; save CAD artifacts; get project context (file listing + text content)
- "temp" project is wiped and recreated on every startup
- Auto-creates project when CAD or file-write is triggered while in "temp"

### `backend/telegram_bridge.py` — Remote Access

- Standalone daemon (separate PM2 process: `ATLAS-TELEGRAM`)
- Uses `python-telegram-bot` with Gemini 2.0 Flash chat session
- Authenticated by `TELEGRAM_USER_ID` — unauthorized users are silently dropped
- Commands: `/start`, `/status` (shows memory usage, PID, model info)
- Same J.A.R.V.I.S. personality as main system

---

## Communication Protocol (Socket.IO Events)

### Client → Server

| Event | Payload | Description |
|---|---|---|
| `start_audio` | `{device_index?, device_name?, muted?}` | Start Gemini Live session |
| `stop_audio` | — | Stop session |
| `pause_audio` / `resume_audio` | — | Mute/unmute mic input |
| `user_input` | `{text}` | Send text message to model |
| `video_frame` | `{image: Blob}` | Send camera frame |
| `confirm_tool` | `{id, confirmed}` | Respond to tool confirmation |
| `generate_cad` | `{prompt}` | Direct CAD generation request |
| `iterate_cad` | `{prompt}` | Iterate on current CAD design |
| `prompt_web_agent` | `{prompt}` | Direct web agent task |
| `discover_printers` | — | Scan network for printers |
| `add_printer` | `{host, name?, type?}` | Manually add a printer |
| `print_stl` | `{stl_path, printer, profile?}` | Slice and print |
| `discover_kasa` | — | Scan for smart home devices |
| `control_kasa` | `{ip, action, value?}` | Control a Kasa device |
| `save_memory` | `{messages, filename?}` | Save chat to file |
| `upload_memory` | `{memory}` | Load memory context into model |
| `get_settings` / `update_settings` | settings object | Read/write app settings |
| `shutdown` | — | Graceful shutdown |

### Server → Client

| Event | Payload | Description |
|---|---|---|
| `status` | `{msg}` | System status messages |
| `audio_data` | `{data: number[]}` | AI voice audio for visualizer |
| `transcription` | `{sender, text}` | Streaming speech-to-text (delta chunks) |
| `cad_data` | `{format, data, file_path?}` | STL model data (base64) |
| `cad_status` | `{status, attempt?, error?}` | CAD generation progress |
| `cad_thought` | `{text}` | Streaming AI thinking for CAD |
| `browser_frame` | `{image, log}` | Web agent screenshot + action log |
| `tool_confirmation_request` | `{id, tool, args}` | Request user approval for tool |
| `auth_status` | `{authenticated}` | Face auth state |
| `auth_frame` | `{image}` | Camera frame during auth |
| `kasa_devices` | `[{ip, alias, model, ...}]` | Device list |
| `kasa_update` | `{ip, is_on, brightness?}` | Single device state change |
| `printer_list` | `[{name, host, port, type}]` or `{printers: [...], badge: boolean}` | Printer list; `badge: true` only when discovered/connected (top bar shows count only then) |
| `print_status_update` | `{printer, state, progress, temps}` | Live print status |
| `slicing_progress` | `{printer, percent, message}` | Slicing progress |
| `settings` | full settings object | Current settings |
| `error` | `{msg}` | Error messages |
| `project_update` | `{project}` | Active project changed |

---

## Gemini Tool Definitions

All tool declarations and default permissions live in **`backend/tool_registry.py`**. The system registers the following tools with the Gemini Live API:

| Tool | Description |
|---|---|
| `generate_cad` | Generate a 3D CAD model from a prompt |
| `iterate_cad` | Modify existing CAD design |
| `run_web_agent` | Launch browser automation task |
| `write_file` | Write content to a file in current project |
| `read_file` | Read a file's content |
| `read_directory` | List directory contents |
| `create_project` | Create a new project folder |
| `switch_project` | Switch active project context |
| `list_projects` | List all available projects |
| `list_smart_devices` | List cached Kasa smart home devices |
| `control_light` | Control a smart light (on/off/brightness/color) |
| `discover_printers` | Discover 3D printers on network |
| `print_stl` | Slice and print an STL file |
| `get_print_status` | Get printer status (progress, temps) |
| `google_search` | Google search (Gemini native) |

Tools with `"behavior": "NON_BLOCKING"` (CAD, web agent, iterate_cad) are dispatched as `asyncio.create_task` without blocking the audio stream.

---

## Configuration

### Environment Variables (`.env`)

```
GEMINI_API_KEY=...          # Required — Google AI Studio API key
FIRECRAWL_API_KEY=...       # Optional — Firecrawl web scraping
TELEGRAM_BOT_TOKEN=...      # Optional — Telegram bot token
TELEGRAM_USER_ID=...        # Optional — Authorized Telegram user ID (numeric)
```

### Settings (`settings.json`)

```json
{
    "face_auth_enabled": false,
    "tool_permissions": {
        "generate_cad": true,
        "run_web_agent": true,
        "write_file": true,
        "read_directory": true,
        "read_file": true,
        "create_project": true,
        "switch_project": true,
        "list_projects": true
    },
    "printers": [],
    "kasa_devices": [],
    "camera_flipped": false
}
```

When `tool_permissions.<tool>` is `true`, user confirmation is requested before execution. When `false`, the tool executes automatically.

---

## Frontend UI

The frontend is a single `App.jsx` (with hooks and shared components) managing a cyberpunk-themed fullscreen interface:

- **Top bar**: App title (Orbitron font), version, FPS counter, **printer count badge** (only when printers are discovered/connected, not saved-but-offline), Kasa device count, mic waveform visualizer, clock, window controls
- **Central visualizer**: R3F 3D audio-reactive sphere (`Visualizer3D.jsx`) with Suspense fallback to 2D canvas; glass panel styling
- **Chat module**: Scrolling transcript with role-based styling (User/You: cyan; ATLAS: magenta; System: amber), Framer Motion entrance, **voice hints** when connected (e.g. “Unmute the mic to use voice” / “Listening — try saying: …”), and text input
- **Tool bar** (bottom): Control-surface styling (edge glow, hover); Power (amber when connected), mic, video, hand tracking, settings, CAD, browser, Kasa, printer — all in glass panel
- **Floating windows**: CAD viewer (STL in Three.js), browser screenshot viewer, Kasa device list, printer management — all draggable via `DraggableWindow`
- **Gesture control**: MediaPipe hand tracking with pinch-to-click, fist-to-drag, cursor smoothing, and snap-to-button
- **Face auth lock screen**: Full-screen overlay with live camera feed during authentication
- **Confirmation popup**: Modal for approving tool executions

**Status messages in chat**: Only whitelisted system messages (e.g. “A.T.L.A.S. Started”, “Model Connected”) appear in the chat; Kasa/printer discovery and similar backend status messages are no longer added to the transcript.

---

## Running the Application

### Development (Two terminals)

```bash
# Terminal 1: Backend
conda activate atlas
python backend/server.py          # Starts on port 8000

# Terminal 2: Frontend
npm run dev                       # Vite dev server on :5173, Electron opens after
```

### Production (PM2 daemon)

```bash
npm run dev    # Starts both PM2 daemons (ATLAS-CORE, ATLAS-TELEGRAM) + Vite + Electron
```

### Tests

```bash
pytest tests/ -v
```

---

## Key Design Decisions

1. **Single Python environment**: All backend dependencies (build123d, mediapipe, playwright, etc.) share one conda env (`atlas`, Python 3.11)
2. **Windows asyncio fix**: `WindowsProactorEventLoopPolicy` is set before any imports to support subprocess creation
3. **No ORM or database**: All state is file-based (JSON settings, JSONL chat logs, STL files in project folders)
4. **Tool confirmation flow**: Async `Future`-based pattern — server creates a future, frontend resolves it via `confirm_tool` event
5. **Auto-reconnect**: AudioLoop has a retry loop that restores last 10 chat messages on reconnection
6. **Non-blocking tool calls**: Long-running tools (CAD, web agent) run as `asyncio.create_task` to avoid blocking the audio stream
7. **PM2 for process management**: Backend runs as a persistent daemon, Electron waits for health check before showing window
8. **Deleted file**: `backend/ada.py` was renamed to `backend/aegis.py` (git status shows `D backend/ada.py`)

---

---

## Improvement Plan Progress (ATLAS Combined)

| Step | Status | Notes |
|------|--------|------|
| **1. Critical bugs** | ✅ Done | save_memory write, request_id, duplicate except, test imports, camera backend |
| **2. HippoMem** | ✅ Done | memory.py wrapper, AudioLoop/server/telegram hooks, config |
| **3A. React hooks** | ✅ Done | 10 hooks extracted; App.jsx reduced |
| **3B. DraggableWindow** | ✅ Done | Shared CAD/Browser overlay component |
| **3C. receive_audio split** | ✅ Done | _push_audio_data, _process_transcription, _finish_turn, _process_tool_calls |
| **3D. AppServices** | ✅ Done | Replaced globals in server.py with `AppServices` container |
| **3E. tool_registry** | ✅ Done | Consolidated in `tool_registry.py`; `tools.py` re-exports for compatibility |
| **4. Code quality** | ✅ Done | Logger in backend; server prints → logger; Error Boundary in React; import dedupe |
| **5. Infrastructure** | ✅ Done | Ruff (pyproject.toml), ESLint, pinned deps, GitHub Actions CI, Electron preload + contextIsolation, Dockerfile |

---

## Recent Changes (UI & Polish)

| Change | Description |
|--------|-------------|
| **Server FastAPI fix** | `server.py`: FastAPI app renamed to `web_app` so `app` can remain the `AppServices` container; `@web_app.on_event("startup")` and `@web_app.get("/status")` restored. |
| **UI modernization** | 3D visualizer (R3F sphere + Suspense fallback), glass panels, Orbitron display font, accent colors (amber/magenta), tool dock edge glow, chat role styling + motion. See `docs/UI_MODERNIZATION_PLAN.md`. |
| **Printer badge** | Backend emits `printer_list` as `{ printers: [...], badge: true\|false }`. Top bar “X Printers” only when `badge === true` (discovered/connected); saved-but-offline printers no longer show a count. |
| **Status message filter** | `useChat.js`: only whitelisted status messages (e.g. A.T.L.A.S. Started/Stopped, Model Connected, Ready for voice, Listening) are added to chat; Kasa/printer discovery and similar messages are omitted. |
| **Voice hints** | `ChatModule`: when connected, shows “Unmute the mic (toolbar) to use voice” or “Listening — try saying: …” with example commands; placeholder text varies by mute state; “You” messages use same cyan style as User. |

---

## Known Issues / Technical Debt

- `App.jsx` reduced via hooks and DraggableWindow; further decomposition possible
- Duplicate `except` block in `printer_agent.py` fixed
- Indentation in `atlas.py` tool-call block normalized (Step 3C)
- `save_memory` write bug fixed
- `authenticator.py` uses platform-specific camera backend (Windows/macOS)
- `web_agent.py` uses `Control+A` for select-all which doesn't work on macOS (should be `Meta+A`)
