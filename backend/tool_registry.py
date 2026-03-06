"""
Consolidated tool definitions for Gemini Live API and confirmation metadata.
All function declarations and default permission (confirmation) behavior live here.
"""

# Default permission: True = require user confirmation before execution
DEFAULT_PERMISSIONS = {
    "generate_cad": True,
    "run_web_agent": True,
    "write_file": True,
    "read_directory": True,
    "read_file": True,
    "create_project": True,
    "switch_project": True,
    "list_projects": True,
    "list_smart_devices": True,
    "control_light": True,
    "discover_printers": True,
    "print_stl": True,
    "get_print_status": True,
    "iterate_cad": True,
}

# All function declarations for Gemini (order preserved for config)
FUNCTION_DECLARATIONS = [
    {
        "name": "generate_cad",
        "description": "Generates a 3D CAD model based on a prompt.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {"type": "STRING", "description": "The description of the object to generate."}
            },
            "required": ["prompt"]
        },
        "behavior": "NON_BLOCKING"
    },
    {
        "name": "run_web_agent",
        "description": "Opens a web browser and performs a task according to the prompt.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
            },
            "required": ["prompt"]
        },
        "behavior": "NON_BLOCKING"
    },
    {
        "name": "write_file",
        "description": "Writes content to a file at the specified path. Overwrites if exists.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "The path of the file to write to."},
                "content": {"type": "STRING", "description": "The content to write to the file."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_directory",
        "description": "Lists the contents of a directory.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"path": {"type": "STRING", "description": "The path of the directory to list."}},
            "required": ["path"]
        }
    },
    {
        "name": "read_file",
        "description": "Reads the content of a file.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"path": {"type": "STRING", "description": "The path of the file to read."}},
            "required": ["path"]
        }
    },
    {
        "name": "create_project",
        "description": "Creates a new project folder to organize files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"name": {"type": "STRING", "description": "The name of the new project."}},
            "required": ["name"]
        }
    },
    {
        "name": "switch_project",
        "description": "Switches the current active project context.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"name": {"type": "STRING", "description": "The name of the project to switch to."}},
            "required": ["name"]
        }
    },
    {
        "name": "list_projects",
        "description": "Lists all available projects.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "list_smart_devices",
        "description": "Lists all available smart home devices (lights, plugs, etc.) on the network.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "control_light",
        "description": "Controls a smart light device.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {"type": "STRING", "description": "The IP address of the device to control. Always prefer the IP address over the alias for reliability."},
                "action": {"type": "STRING", "description": "The action to perform: 'turn_on', 'turn_off', or 'set'."},
                "brightness": {"type": "INTEGER", "description": "Optional brightness level (0-100)."},
                "color": {"type": "STRING", "description": "Optional color name (e.g., 'red', 'cool white') or 'warm'."}
            },
            "required": ["target", "action"]
        }
    },
    {
        "name": "discover_printers",
        "description": "Discovers 3D printers available on the local network.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "print_stl",
        "description": "Prints an STL file to a 3D printer. Handles slicing the STL to G-code and uploading to the printer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "stl_path": {"type": "STRING", "description": "Path to STL file, or 'current' for the most recent CAD model."},
                "printer": {"type": "STRING", "description": "Printer name or IP address."},
                "profile": {"type": "STRING", "description": "Optional slicer profile name."}
            },
            "required": ["stl_path", "printer"]
        }
    },
    {
        "name": "get_print_status",
        "description": "Gets the current status of a 3D printer including progress, time remaining, and temperatures.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"printer": {"type": "STRING", "description": "Printer name or IP address."}},
            "required": ["printer"]
        }
    },
    {
        "name": "iterate_cad",
        "description": "Modifies or iterates on the current CAD design based on user feedback. Use this when the user asks to adjust, change, modify, or iterate on the existing 3D model (e.g., 'make it taller', 'add a handle', 'reduce the thickness').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {"type": "STRING", "description": "The changes or modifications to apply to the current design."}
            },
            "required": ["prompt"]
        },
        "behavior": "NON_BLOCKING"
    },
]


def get_tools_for_gemini():
    """Returns the tools list for Gemini LiveConnectConfig (google_search + function_declarations)."""
    return [
        {"google_search": {}},
        {"function_declarations": FUNCTION_DECLARATIONS}
    ]
