"""
Tests for the Telegram bridge's tool dispatch (list_smart_devices, control_light,
discover_printers, get_print_status). Requires GEMINI_API_KEY to be set (non-empty)
in the environment, same as test_web_agent.py, since telegram_bridge.py constructs
a genai.Client at import time.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import telegram_bridge


def make_device(alias, ip, is_on=False, is_bulb=False, is_plug=False, is_strip=False, is_dimmer=False):
    return SimpleNamespace(
        alias=alias, is_on=is_on, is_bulb=is_bulb, is_plug=is_plug, is_strip=is_strip, is_dimmer=is_dimmer,
    )


@pytest.fixture(autouse=True)
def fake_agents(monkeypatch):
    """Replace the module-level kasa_agent/printer_agent with fakes for every test."""
    fake_kasa = SimpleNamespace(
        devices={},
        turn_on=AsyncMock(return_value=True),
        turn_off=AsyncMock(return_value=True),
        set_brightness=AsyncMock(return_value=True),
        set_color=AsyncMock(return_value=True),
    )
    fake_printer = SimpleNamespace(
        discover_printers=AsyncMock(return_value=[]),
        get_print_status=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(telegram_bridge, "kasa_agent", fake_kasa)
    monkeypatch.setattr(telegram_bridge, "printer_agent", fake_printer)
    return fake_kasa, fake_printer


class TestListSmartDevices:
    @pytest.mark.asyncio
    async def test_empty_cache(self, fake_agents):
        result = await telegram_bridge.execute_tool("list_smart_devices", {})
        assert "No devices found" in result

    @pytest.mark.asyncio
    async def test_lists_cached_devices(self, fake_agents):
        fake_kasa, _ = fake_agents
        fake_kasa.devices = {
            "10.0.0.5": make_device("Bedroom Light", "10.0.0.5", is_on=True, is_bulb=True),
            "10.0.0.6": make_device("Desk Plug", "10.0.0.6", is_on=False, is_plug=True),
        }
        result = await telegram_bridge.execute_tool("list_smart_devices", {})
        assert "Bedroom Light" in result and "[ON]" in result
        assert "Desk Plug" in result and "[OFF]" in result


class TestControlLight:
    @pytest.mark.asyncio
    async def test_turn_on(self, fake_agents):
        fake_kasa, _ = fake_agents
        result = await telegram_bridge.execute_tool("control_light", {"target": "10.0.0.5", "action": "turn_on"})
        fake_kasa.turn_on.assert_awaited_once_with("10.0.0.5")
        assert "Turned ON" in result

    @pytest.mark.asyncio
    async def test_turn_off(self, fake_agents):
        fake_kasa, _ = fake_agents
        result = await telegram_bridge.execute_tool("control_light", {"target": "10.0.0.5", "action": "turn_off"})
        fake_kasa.turn_off.assert_awaited_once_with("10.0.0.5")
        assert "Turned OFF" in result

    @pytest.mark.asyncio
    async def test_set_brightness_and_color(self, fake_agents):
        fake_kasa, _ = fake_agents
        result = await telegram_bridge.execute_tool(
            "control_light", {"target": "10.0.0.5", "action": "set", "brightness": 50, "color": "red"}
        )
        fake_kasa.set_brightness.assert_awaited_once_with("10.0.0.5", 50)
        fake_kasa.set_color.assert_awaited_once_with("10.0.0.5", "red")
        assert "Set brightness to 50" in result and "Set color to red" in result

    @pytest.mark.asyncio
    async def test_device_not_found(self, fake_agents):
        fake_kasa, _ = fake_agents
        fake_kasa.turn_on = AsyncMock(return_value=False)
        result = await telegram_bridge.execute_tool("control_light", {"target": "9.9.9.9", "action": "turn_on"})
        assert "not found or unreachable" in result

    @pytest.mark.asyncio
    async def test_missing_args(self, fake_agents):
        result = await telegram_bridge.execute_tool("control_light", {"target": "10.0.0.5"})
        assert "Missing required" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, fake_agents):
        result = await telegram_bridge.execute_tool("control_light", {"target": "10.0.0.5", "action": "explode"})
        assert "Unknown action" in result


class TestDiscoverPrinters:
    @pytest.mark.asyncio
    async def test_none_found(self, fake_agents):
        result = await telegram_bridge.execute_tool("discover_printers", {})
        assert "No printers found" in result

    @pytest.mark.asyncio
    async def test_found(self, fake_agents):
        _, fake_printer = fake_agents
        fake_printer.discover_printers = AsyncMock(
            return_value=[{"name": "Creality K1", "host": "10.0.0.142", "port": 7125, "printer_type": "moonraker"}]
        )
        result = await telegram_bridge.execute_tool("discover_printers", {})
        assert "Creality K1" in result and "10.0.0.142" in result


class TestGetPrintStatus:
    @pytest.mark.asyncio
    async def test_not_found(self, fake_agents):
        result = await telegram_bridge.execute_tool("get_print_status", {"printer": "Unknown Printer"})
        assert "Could not get status" in result

    @pytest.mark.asyncio
    async def test_missing_arg(self, fake_agents):
        result = await telegram_bridge.execute_tool("get_print_status", {})
        assert "Missing required" in result

    @pytest.mark.asyncio
    async def test_found(self, fake_agents):
        _, fake_printer = fake_agents
        fake_printer.get_print_status = AsyncMock(return_value=SimpleNamespace(
            printer="Creality K1", state="printing", progress_percent=42.5,
            time_remaining="1h 2m", time_elapsed="30m", filename="benchy.gcode",
            temperatures={"hotend": {"current": 210.0, "target": 215.0}, "bed": {"current": 60.0, "target": 60.0}},
        ))
        result = await telegram_bridge.execute_tool("get_print_status", {"printer": "Creality K1"})
        assert "Creality K1" in result and "42.5%" in result and "Hotend" in result and "Bed" in result


class TestExecuteToolDispatch:
    @pytest.mark.asyncio
    async def test_unknown_tool(self, fake_agents):
        result = await telegram_bridge.execute_tool("delete_everything", {})
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_handler_exception_is_caught(self, fake_agents):
        fake_kasa, _ = fake_agents
        fake_kasa.turn_on = AsyncMock(side_effect=RuntimeError("network unreachable"))
        result = await telegram_bridge.execute_tool("control_light", {"target": "10.0.0.5", "action": "turn_on"})
        assert "failed" in result.lower()
