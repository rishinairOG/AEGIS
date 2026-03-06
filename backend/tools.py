"""
Legacy re-export of tool definitions from tool_registry for backward compatibility.
Prefer importing from tool_registry in new code.
"""
from tool_registry import FUNCTION_DECLARATIONS, DEFAULT_PERMISSIONS

# Named tool dicts (tools.py originally had generate_cad_prototype, write_file, read_directory, read_file)
write_file_tool = next((t for t in FUNCTION_DECLARATIONS if t["name"] == "write_file"), None)
read_directory_tool = next((t for t in FUNCTION_DECLARATIONS if t["name"] == "read_directory"), None)
read_file_tool = next((t for t in FUNCTION_DECLARATIONS if t["name"] == "read_file"), None)
generate_cad_prototype_tool = next((t for t in FUNCTION_DECLARATIONS if t["name"] == "generate_cad"), None)

tools_list = [{"function_declarations": FUNCTION_DECLARATIONS}]
