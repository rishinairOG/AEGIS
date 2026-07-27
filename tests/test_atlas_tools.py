"""
Tests for AI Tool Definitions and Handlers.
"""
import pytest
import os
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


class TestToolDefinitions:
    """Test tool definition schemas."""
    
    def test_generate_cad_tool_schema(self):
        """Test generate_cad tool has correct schema."""
        from atlas import generate_cad
        
        assert generate_cad['name'] == 'generate_cad'
        assert 'description' in generate_cad
        assert 'parameters' in generate_cad
        assert generate_cad['parameters']['type'] == 'OBJECT'
        assert 'prompt' in generate_cad['parameters']['properties']
        print(f"generate_cad tool: {generate_cad['name']}")
    
    def test_run_web_agent_tool_schema(self):
        """Test run_web_agent tool has correct schema."""
        from atlas import run_web_agent
        
        assert run_web_agent['name'] == 'run_web_agent'
        assert 'description' in run_web_agent
        assert 'parameters' in run_web_agent
        assert 'prompt' in run_web_agent['parameters']['properties']
        print(f"run_web_agent tool: {run_web_agent['name']}")
    
    def test_print_stl_tool_schema(self):
        """Test print_stl tool has correct schema."""
        from atlas import print_stl_tool
        
        assert print_stl_tool['name'] == 'print_stl'
        assert 'description' in print_stl_tool
        assert 'parameters' in print_stl_tool
        print(f"print_stl tool: {print_stl_tool['name']}")
    
    def test_discover_printers_tool_schema(self):
        """Test discover_printers tool has correct schema."""
        from atlas import discover_printers_tool
        
        assert discover_printers_tool['name'] == 'discover_printers'
        assert 'description' in discover_printers_tool
        print(f"discover_printers tool: {discover_printers_tool['name']}")
    
    def test_list_smart_devices_tool_schema(self):
        """Test list_smart_devices tool has correct schema."""
        from atlas import list_smart_devices_tool
        
        assert list_smart_devices_tool['name'] == 'list_smart_devices'
        assert 'description' in list_smart_devices_tool
        print(f"list_smart_devices tool: {list_smart_devices_tool['name']}")
    
    def test_control_light_tool_schema(self):
        """Test control_light tool has correct schema."""
        from atlas import control_light_tool
        
        assert control_light_tool['name'] == 'control_light'
        assert 'parameters' in control_light_tool
        props = control_light_tool['parameters']['properties']
        assert 'target' in props
        assert 'action' in props
        print(f"control_light tool: {control_light_tool['name']}")
    
    def test_list_projects_tool_schema(self):
        """Test list_projects tool has correct schema."""
        from atlas import list_projects_tool
        
        assert list_projects_tool['name'] == 'list_projects'
        print(f"list_projects tool: {list_projects_tool['name']}")
    
    def test_iterate_cad_tool_schema(self):
        """Test iterate_cad tool has correct schema."""
        from atlas import iterate_cad_tool
        
        assert iterate_cad_tool['name'] == 'iterate_cad'
        print(f"iterate_cad tool: {iterate_cad_tool['name']}")


class TestAudioLoopClass:
    """Test AudioLoop class structure."""
    
    def test_audioloop_class_exists(self):
        """Test AudioLoop class can be imported."""
        from atlas import AudioLoop
        assert AudioLoop is not None
        print("AudioLoop class imported successfully")
    
    def test_audioloop_methods(self):
        """Test AudioLoop has required methods."""
        from atlas import AudioLoop
        
        required_methods = [
            'run',
            'stop',
            'send_frame',
            'listen_audio',
            'receive_audio',
            'play_audio',
            'handle_cad_request',
            'handle_web_agent_request',
            'resolve_tool_confirmation',
            'update_permissions',
            'set_paused',
            'clear_audio_queue',
        ]
        
        for method in required_methods:
            assert hasattr(AudioLoop, method), f"Missing method: {method}"
            print(f"  ✓ {method}")


class TestConnectionErrorClassification:
    """Test _classify_connection_error so quota/auth failures don't silently loop."""

    def test_quota_errors(self):
        from atlas import AudioLoop
        # The real 1011 message seen in production, plus other quota phrasings.
        quota_msgs = [
            "received 1011 (internal error) You exceeded your current quota, please check your plan and billing details.",
            "429 RESOURCE_EXHAUSTED",
            "Quota exceeded for quota metric",
        ]
        for m in quota_msgs:
            assert AudioLoop._classify_connection_error(Exception(m)) == "quota", m

    def test_auth_errors(self):
        from atlas import AudioLoop
        auth_msgs = [
            "403 PERMISSION_DENIED: API key not valid",
            "401 Unauthenticated",
            "Invalid API key provided",
        ]
        for m in auth_msgs:
            assert AudioLoop._classify_connection_error(Exception(m)) == "auth", m

    def test_transient_errors(self):
        from atlas import AudioLoop
        transient_msgs = [
            "Connection closed abnormally",
            "received 1006 (connection closed abnormally)",
            "Temporary failure in name resolution",
        ]
        for m in transient_msgs:
            assert AudioLoop._classify_connection_error(Exception(m)) == "transient", m


class TestToolDispatch:
    """The registry refactor: tools dispatch by naming convention _tool_<name>."""

    def test_every_declared_tool_has_a_handler(self):
        from atlas import AudioLoop
        from tool_registry import FUNCTION_DECLARATIONS
        missing = [d["name"] for d in FUNCTION_DECLARATIONS if not hasattr(AudioLoop, f"_tool_{d['name']}")]
        assert not missing, f"declared tools with no _tool_ handler: {missing}"

    def test_no_orphan_handlers(self):
        # Every _tool_<name> method should correspond to a declared tool
        # (helper methods like _tool_control_light are fine; _kasa_device_dict
        # is deliberately NOT named _tool_*).
        from atlas import AudioLoop
        from tool_registry import FUNCTION_DECLARATIONS
        declared = {d["name"] for d in FUNCTION_DECLARATIONS}
        handlers = {n[len("_tool_"):] for n in dir(AudioLoop) if n.startswith("_tool_")}
        orphans = handlers - declared
        assert not orphans, f"_tool_ methods with no matching declaration: {orphans}"

    @pytest.mark.asyncio
    async def test_list_projects_handler(self):
        from types import SimpleNamespace
        from atlas import AudioLoop
        fake_self = SimpleNamespace(project_manager=SimpleNamespace(list_projects=lambda: ["a", "b"]))
        result = await AudioLoop._tool_list_projects(fake_self, SimpleNamespace(args={}))
        assert result == {"result": "Available projects: a, b"}

    @pytest.mark.asyncio
    async def test_generate_cad_is_fire_and_forget(self):
        import asyncio
        from types import SimpleNamespace
        from atlas import AudioLoop
        called = {}
        async def fake_handle(prompt):
            called["prompt"] = prompt
        fake_self = SimpleNamespace(handle_cad_request=fake_handle)
        result = await AudioLoop._tool_generate_cad(fake_self, SimpleNamespace(args={"prompt": "a cube"}))
        await asyncio.sleep(0)  # let the created task run
        assert result is None  # no FunctionResponse for fire-and-forget
        assert called.get("prompt") == "a cube"

    @pytest.mark.asyncio
    async def test_confirm_auto_allows_when_permission_disabled(self):
        from types import SimpleNamespace
        from atlas import AudioLoop
        fake_self = SimpleNamespace(permissions={"control_light": False}, on_tool_confirmation=lambda x: None)
        ok = await AudioLoop._confirm_tool(fake_self, SimpleNamespace(name="control_light", id="1", args={}), [])
        assert ok is True

    @pytest.mark.asyncio
    async def test_confirm_allows_when_no_confirmation_ui(self):
        from types import SimpleNamespace
        from atlas import AudioLoop
        fake_self = SimpleNamespace(permissions={}, on_tool_confirmation=None)
        ok = await AudioLoop._confirm_tool(fake_self, SimpleNamespace(name="write_file", id="1", args={}), [])
        assert ok is True


class TestAgentUsageRecording:
    """record_agent_usage folds CAD/web agent usage into the shared tracker + emits."""

    def _fake_usage(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            prompt_tokens_details=[SimpleNamespace(modality=SimpleNamespace(name="TEXT"), token_count=100)],
            response_tokens_details=[SimpleNamespace(modality=SimpleNamespace(name="TEXT"), token_count=200)],
            prompt_token_count=100,
            response_token_count=200,
        )

    def test_records_and_emits(self):
        from types import SimpleNamespace
        from atlas import AudioLoop
        from usage_tracker import UsageTracker

        emitted = []
        # Exercise the method logic without building a full (heavy) AudioLoop.
        fake_self = SimpleNamespace(usage_tracker=UsageTracker(), on_usage=lambda s: emitted.append(s))
        AudioLoop.record_agent_usage(fake_self, "gemini-3-pro-preview", self._fake_usage())

        assert emitted, "on_usage should have been called"
        assert emitted[-1]["total_tokens"] == 300
        assert emitted[-1]["est_cost_usd"] > 0

    def test_per_response_accumulates(self):
        from types import SimpleNamespace
        from atlas import AudioLoop
        from usage_tracker import UsageTracker

        emitted = []
        fake_self = SimpleNamespace(usage_tracker=UsageTracker(), on_usage=lambda s: emitted.append(s))
        # Two agent calls (per-response) should sum, not overwrite.
        AudioLoop.record_agent_usage(fake_self, "gemini-3-pro-preview", self._fake_usage())
        AudioLoop.record_agent_usage(fake_self, "gemini-3-pro-preview", self._fake_usage())
        assert emitted[-1]["total_tokens"] == 600


class TestFileOperations:
    """Test file operation handlers."""

    def test_read_directory_method_exists(self):
        """Test handle_read_directory exists."""
        from atlas import AudioLoop
        assert hasattr(AudioLoop, 'handle_read_directory')
    
    def test_read_file_method_exists(self):
        """Test handle_read_file exists."""
        from atlas import AudioLoop
        assert hasattr(AudioLoop, 'handle_read_file')
    
    def test_write_file_method_exists(self):
        """Test handle_write_file exists."""
        from atlas import AudioLoop
        assert hasattr(AudioLoop, 'handle_write_file')


class TestLiveConnectConfig:
    """Test Gemini Live Connect configuration."""
    
    def test_config_exists(self):
        """Test config is defined."""
        from atlas import config
        assert config is not None
        print("LiveConnectConfig exists")
    
    def test_config_has_audio_modality(self):
        """Test config includes audio modality."""
        from atlas import config
        assert 'AUDIO' in config.response_modalities
        print("Audio modality configured")


class TestToolPermissions:
    """Test tool permission handling."""
    
    def test_update_permissions_method(self):
        """Test update_permissions method exists."""
        from atlas import AudioLoop
        assert hasattr(AudioLoop, 'update_permissions')
        print("update_permissions method exists")


class TestAgentImports:
    """Test agent module imports in atlas.py."""
    
    def test_cad_agent_import(self):
        """Test CadAgent is imported."""
        from atlas import CadAgent
        assert CadAgent is not None
        print("CadAgent imported")
    
    def test_web_agent_import(self):
        """Test WebAgent is imported."""
        from atlas import WebAgent
        assert WebAgent is not None
        print("WebAgent imported")
    
    def test_kasa_agent_import(self):
        """Test KasaAgent is imported."""
        from atlas import KasaAgent
        assert KasaAgent is not None
        print("KasaAgent imported")
    
    def test_printer_agent_import(self):
        """Test PrinterAgent is imported."""
        from atlas import PrinterAgent
        assert PrinterAgent is not None
        print("PrinterAgent imported")


class TestToolConfirmation:
    """Test tool confirmation handling."""
    
    def test_resolve_tool_confirmation_method(self):
        """Test resolve_tool_confirmation exists."""
        from atlas import AudioLoop
        assert hasattr(AudioLoop, 'resolve_tool_confirmation')
        print("resolve_tool_confirmation method exists")
